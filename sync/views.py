from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.text import slugify
from .forms import TripForm, ProposalForm
from .models import Trip, TripMember, DestinationProposal, Vote
import json
from datetime import timedelta
from .models import Trip, TripMember, DestinationProposal, Vote, Availability
from django.utils import timezone
from .llm import generate_itinerary as llm_generate
from .models import Trip, TripMember, DestinationProposal, Vote, Availability, Itinerary, ItineraryDay, ItineraryActivity


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

    # Build date range
    dates = []
    if trip.departure_date and trip.return_date:
        current = trip.departure_date
        while current <= trip.return_date:
            dates.append(current)
            current += timedelta(days=1)

    # Build availability grid: {user_id: {date_str: status}}

    avail_qs = Availability.objects.filter(trip=trip).select_related('user')
    grid = {}
    for a in avail_qs:
        grid.setdefault(a.user_id, {})[str(a.date)] = a.status

    # Get itinerary if it exists
    itinerary = None
    try:
        itinerary = trip.itinerary
    except:
        pass

    return render(request, 'sync/trip_detail.html', {
        'trip': trip,
        'members': members,
        'proposals_with_scores': proposals_with_scores,
        'dates': dates,
        'grid': grid,
        'itinerary': itinerary,
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

@login_required
def availability(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    
    if request.method == 'POST':
        try:
            date = request.POST.get('date')
            status = request.POST.get('status')
            print(f"Saving availability: trip={trip.id}, user={request.user.id}, date={date}, status={status}")
            Availability.objects.update_or_create(
                trip=trip,
                user=request.user,
                date=date,
                defaults={'status': status}
            )
            print("Saved successfully!")
            return JsonResponse({'ok': True})
        except Exception as e:
            print(f"ERROR: {e}")
            return JsonResponse({'error': str(e)}, status=500)


    return JsonResponse({'error': 'GET not allowed'}, status=405)

@login_required
def itinerary_generate(request, slug):
    trip = get_object_or_404(Trip, slug=slug)

    if request.user != trip.lead:
        return redirect('trip_detail', slug=slug)

    if request.method == 'POST':
        itinerary, _ = Itinerary.objects.get_or_create(trip=trip)
        itinerary.status = 'generating'
        itinerary.save()

        try:
            data, raw = llm_generate(trip)

            itinerary.days.all().delete()

            for d in data['days']:
                day = ItineraryDay.objects.create(
                    itinerary=itinerary,
                    day_number=d['day_number'],
                    date=d['date'],
                    location=d['location'],
                    theme=d.get('theme', ''),
                )
                for a in d['activities']:
                    ItineraryActivity.objects.create(
                        day=day,
                        time_slot=a['time_slot'],
                        title=a['title'],
                        description=a.get('description', ''),
                        category=a['category'],
                    )

            itinerary.status = 'ready'
            itinerary.llm_raw = raw
            itinerary.generated_at = timezone.now()
            itinerary.save()

        except Exception as e:
            print(f"LLM Error: {e}")
            itinerary.status = 'failed'
            itinerary.save()

    return redirect('trip_detail', slug=slug)