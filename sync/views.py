from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.text import slugify
from .forms import TripForm, ProposalForm
from .models import Trip, TripMember, DestinationProposal, Vote


@login_required
def dashboard(request):
    trips = request.user.trips.all()
    return render(request, 'sync/dashboard.html', {'trips': trips})


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def trip_create(request):
    if request.method == 'POST':
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.lead = request.user
            base_slug = slugify(trip.name)
            slug = base_slug
            counter = 1
            while Trip.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            trip.slug = slug
            trip.save()
            TripMember.objects.create(
                trip=trip,
                user=request.user,
                role='lead'
            )
            return redirect('trip_detail', slug=trip.slug)
    else:
        form = TripForm()
    return render(request, 'sync/trip_create.html', {'form': form})


@login_required
def trip_detail(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    members = TripMember.objects.filter(trip=trip).select_related('user')
    proposals = trip.proposals.all().prefetch_related('votes')

    user_votes = {
        v.proposal_id: v.score
        for v in Vote.objects.filter(
            proposal__trip=trip,
            user=request.user
        )
    }

    proposals_with_scores = []
    for p in proposals:
        total = sum(v.score for v in p.votes.all())
        proposals_with_scores.append({
            'proposal': p,
            'total': total,
            'user_vote': user_votes.get(p.id),
        })

    proposals_with_scores.sort(key=lambda x: x['total'], reverse=True)

    return render(request, 'sync/trip_detail.html', {
        'trip': trip,
        'members': members,
        'proposals_with_scores': proposals_with_scores,
    })


@login_required
def trip_join(request, token):
    trip = get_object_or_404(Trip, invite_token=token)
    already_member = TripMember.objects.filter(
        trip=trip, user=request.user
    ).exists()
    if not already_member:
        TripMember.objects.create(
            trip=trip,
            user=request.user,
            role='member'
        )
    return redirect('trip_detail', slug=trip.slug)


@login_required
def proposal_create(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    if request.method == 'POST':
        form = ProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.trip = trip
            proposal.proposed_by = request.user
            proposal.save()
            return redirect('trip_detail', slug=trip.slug)
    else:
        form = ProposalForm()
    return render(request, 'sync/proposal_create.html', {
        'form': form,
        'trip': trip,
    })


@login_required
def vote(request, proposal_id):
    proposal = get_object_or_404(DestinationProposal, id=proposal_id)
    score = int(request.POST.get('score'))
    Vote.objects.update_or_create(
        proposal=proposal,
        user=request.user,
        defaults={'score': score}
    )
    return redirect('trip_detail', slug=proposal.trip.slug)

@login_required
def trip_edit(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    if request.user != trip.lead:
        return redirect('trip_detail', slug=slug)
    if request.method == 'POST':
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            form.save()
            return redirect('trip_detail', slug=slug)
    else:
        form = TripForm(instance=trip)
    return render(request, 'sync/trip_edit.html', {'form': form, 'trip': trip})


@login_required
def proposal_edit(request, proposal_id):
    proposal = get_object_or_404(DestinationProposal, id=proposal_id)
    if request.user != proposal.proposed_by:
        return redirect('trip_detail', slug=proposal.trip.slug)
    if request.method == 'POST':
        form = ProposalForm(request.POST, instance=proposal)
        if form.is_valid():
            form.save()
            return redirect('trip_detail', slug=proposal.trip.slug)
    else:
        form = ProposalForm(instance=proposal)
    return render(request, 'sync/proposal_edit.html', {
        'form': form,
        'proposal': proposal,
    })