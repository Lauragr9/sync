from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from .forms import TripForm
from .models import Trip, TripMember


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
            trip.slug = trip.name.lower().replace(' ', '-')
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
    return render(request, 'sync/trip_detail.html', {
        'trip': trip,
        'members': members,
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