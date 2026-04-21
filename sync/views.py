from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils.text import slugify
from .forms import AvailabilityForm, LoginForm, ProposalForm, SignUpForm, TripForm
from .models import Trip, TripMember, DestinationProposal, Vote
import json
from datetime import timedelta
from .models import Trip, TripMember, DestinationProposal, Vote, Availability
from django.utils import timezone
from .llm import generate_itinerary as llm_generate
from .models import Trip, TripMember, DestinationProposal, Vote, Availability, Itinerary, ItineraryDay, ItineraryActivity, PackingItem
from django.http import HttpResponse


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

def _trip_theme(trip):
    MONTH_THEMES = {
        1: 'frost', 2: 'frost',
        3: 'bloom', 4: 'bloom',
        5: 'ocean', 6: 'ocean',
        7: 'golden', 8: 'golden',
        9: 'auburn', 10: 'auburn',
        11: 'dusk', 12: 'dusk',
    }
    FALLBACK = ['ocean', 'golden', 'bloom', 'auburn', 'dusk', 'frost']
    if trip.departure_date:
        return MONTH_THEMES[trip.departure_date.month]
    return FALLBACK[trip.id % len(FALLBACK)]


@login_required
def dashboard(request):
    from datetime import date as date_type
    today = date_type.today()

    trips = request.user.trips.all()
    upcoming = trips.filter(departure_date__gte=today).order_by('departure_date')
    next_trip = upcoming.first()
    days_until = (next_trip.departure_date - today).days if next_trip else None

    month = today.month
    if month in (3, 4, 5):
        season = 'Spring'
    elif month in (6, 7, 8):
        season = 'Summer'
    elif month in (9, 10, 11):
        season = 'Autumn'
    else:
        season = 'Winter'

    trips_with_themes = [{'trip': t, 'theme': _trip_theme(t)} for t in trips]

    return render(request, 'sync/dashboard.html', {
        'trips': trips,
        'trips_with_themes': trips_with_themes,
        'next_trip': next_trip,
        'days_until': days_until,
        'upcoming_count': upcoming.count(),
        'season': season,
    })


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
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
    availability_form = AvailabilityForm(trip=trip)

    user_votes = {
        v.proposal_id: v.score
        for v in Vote.objects.filter(
            proposal__trip=trip,
            user=request.user
        )
    }

    itineraries_by_proposal = {
        it.proposal_id: it
        for it in trip.itineraries.select_related('proposal')
    }

    proposals_with_scores = []
    for p in proposals:
        total = sum(v.score for v in p.votes.all())
        proposals_with_scores.append({
            'proposal': p,
            'total': total,
            'user_vote': user_votes.get(p.id),
            'itinerary': itineraries_by_proposal.get(p.id),
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

    my_availability = avail_qs.filter(user=request.user).order_by('date')

    packing_items = trip.packing_items.select_related('added_by').order_by('category', 'name')

    return render(request, 'sync/trip_detail.html', {
        'trip': trip,
        'members': members,
        'proposals_with_scores': proposals_with_scores,
        'dates': dates,
        'grid': grid,
        'availability_form': availability_form,
        'my_availability': my_availability,
        'packing_items': packing_items,
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
            messages.success(request, f'{proposal.city} added as a destination proposal.')
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
    labels = {1: 'Yes', 0: 'Maybe', -1: 'No'}
    messages.success(request, f'Voted "{labels[score]}" for {proposal.city}.')
    return redirect('trip_detail', slug=proposal.trip.slug)

@login_required
def trip_confirm(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    if request.user != trip.lead or request.method != 'POST':
        return redirect('trip_detail', slug=slug)

    proposal_id = request.POST.get('proposal_id')
    proposal = get_object_or_404(DestinationProposal, id=proposal_id, trip=trip)
    trip.confirmed_proposal = proposal
    trip.status = 'confirmed'
    trip.save()
    messages.success(request, f'{proposal.city} confirmed as the destination!')
    return redirect('trip_detail', slug=slug)


@login_required
def trip_unconfirm(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    if request.user != trip.lead or request.method != 'POST':
        return redirect('trip_detail', slug=slug)
    trip.confirmed_proposal = None
    trip.status = 'planning'
    trip.save()
    messages.success(request, 'Destination unconfirmed. Trip is back to planning.')
    return redirect('trip_detail', slug=slug)


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
def proposal_delete(request, proposal_id):
    proposal = get_object_or_404(DestinationProposal, id=proposal_id)
    if request.user != proposal.proposed_by:
        return redirect('trip_detail', slug=proposal.trip.slug)
    if request.method == 'POST':
        slug = proposal.trip.slug
        city = proposal.city
        proposal.delete()
        messages.success(request, f'{city} removed from proposals.')
        return redirect('trip_detail', slug=slug)
    return render(request, 'sync/proposal_confirm_delete.html', {'proposal': proposal})


@login_required
def availability(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    
    if request.method == 'POST':
        form = AvailabilityForm(request.POST, trip=trip)
        if not form.is_valid():
            return JsonResponse({
                'ok': False,
                'message': 'Please fix the availability form and try again.',
                'errors': form.errors.get_json_data(),
            }, status=400)

        cleaned_date = form.cleaned_data['date']
        cleaned_status = form.cleaned_data['status']
        Availability.objects.update_or_create(
            trip=trip,
            user=request.user,
            date=cleaned_date,
            defaults={'status': cleaned_status}
        )
        return JsonResponse({
            'ok': True,
            'message': 'Availability saved!',
            'date': cleaned_date.isoformat(),
            'status': cleaned_status,
        })


    return JsonResponse({'error': 'GET not allowed'}, status=405)

@login_required
def itinerary_generate(request, slug):
    trip = get_object_or_404(Trip, slug=slug)

    if request.user != trip.lead:
        return redirect('trip_detail', slug=slug)

    if request.method == 'POST':
        proposal_id = request.POST.get('proposal_id')
        if proposal_id:
            proposals = trip.proposals.filter(id=proposal_id)
        else:
            proposals = trip.proposals.all()

        if not proposals.exists():
            messages.error(request, 'Add at least one destination proposal first.')
            return redirect('trip_detail', slug=slug)

        for proposal in proposals:
            itinerary, _ = Itinerary.objects.get_or_create(trip=trip, proposal=proposal)
            itinerary.status = 'generating'
            itinerary.save()

            try:
                data, raw = llm_generate(trip, proposal)
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
                print(f"LLM Error for {proposal.city}: {e}")
                itinerary.status = 'failed'
                itinerary.save()

        label = proposals.first().city if proposal_id else 'all destinations'
        messages.success(request, f'Itinerary generated for {label}!')

    return redirect('trip_detail', slug=slug)
@login_required
def packing_add(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', '').strip()
        if name:
            PackingItem.objects.create(trip=trip, name=name, category=category, added_by=request.user)
            messages.success(request, f'"{name}" added to the packing list.')
    return redirect('trip_detail', slug=slug)



@login_required
def packing_toggle(request, item_id):
    item = get_object_or_404(PackingItem, id=item_id)
    if request.method == 'POST':
        item.is_packed = not item.is_packed
        item.save()
    return redirect('trip_detail', slug=item.trip.slug)


@login_required
def packing_delete(request, item_id):
    item = get_object_or_404(PackingItem, id=item_id)
    if request.method == 'POST':
        slug = item.trip.slug
        name = item.name
        item.delete()
        messages.success(request, f'"{name}" removed from the packing list.')
        return redirect('trip_detail', slug=slug)
    return redirect('trip_detail', slug=item.trip.slug)


@login_required
def itinerary_pdf(request, slug, proposal_id):
    trip = get_object_or_404(Trip, slug=slug)
    itinerary = get_object_or_404(Itinerary, trip=trip, proposal_id=proposal_id, status='ready')
    return render(request, 'sync/itinerary_pdf.html', {
        'trip': trip,
        'itinerary': itinerary,
    })