import uuid
from django.db import models
from django.contrib.auth.models import User


class Trip(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
    ]
    BUDGET_CHOICES = [
        ('budget', 'Budget'),
        ('mid', 'Mid-range'),
        ('luxury', 'Luxury'),
    ]

    name           = models.CharField(max_length=200)
    slug           = models.SlugField(unique=True, blank=True)
    description    = models.TextField(blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    departure_date = models.DateField(null=True, blank=True)
    return_date    = models.DateField(null=True, blank=True)
    budget_range   = models.CharField(max_length=20, choices=BUDGET_CHOICES, default='mid')
    invite_token   = models.UUIDField(default=uuid.uuid4, unique=True)
    lead           = models.ForeignKey(User, on_delete=models.SET_NULL,
                         null=True, related_name='led_trips')
    members        = models.ManyToManyField(User, through='TripMember',
                         related_name='trips')
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TripMember(models.Model):
    ROLE_CHOICES = [('lead', 'Lead'), ('member', 'Member')]

    trip      = models.ForeignKey(Trip, on_delete=models.CASCADE)
    user      = models.ForeignKey(User, on_delete=models.CASCADE)
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'user')

    def __str__(self):
        return f'{self.user.username} → {self.trip.name}'


class DestinationProposal(models.Model):
    trip        = models.ForeignKey(Trip, on_delete=models.CASCADE,
                      related_name='proposals')
    proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    city        = models.CharField(max_length=100)
    country     = models.CharField(max_length=100)
    notes       = models.TextField(blank=True)
    image_url   = models.URLField(blank=True) 
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.city}, {self.country}'


class Vote(models.Model):
    SCORE_CHOICES = [(1, 'Yes'), (0, 'Maybe'), (-1, 'No')]

    proposal = models.ForeignKey(DestinationProposal, on_delete=models.CASCADE,
                   related_name='votes')
    user     = models.ForeignKey(User, on_delete=models.CASCADE)
    score    = models.IntegerField(choices=SCORE_CHOICES)

    class Meta:
        unique_together = ('proposal', 'user')


class Availability(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('maybe', 'Maybe'),
        ('unavailable', 'Unavailable'),
    ]

    trip   = models.ForeignKey(Trip, on_delete=models.CASCADE,
                related_name='availability')
    user   = models.ForeignKey(User, on_delete=models.CASCADE)
    date   = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('trip', 'user', 'date')


class Itinerary(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    trip         = models.ForeignKey(Trip, on_delete=models.CASCADE,
                       related_name='itineraries')
    proposal     = models.ForeignKey('DestinationProposal', on_delete=models.CASCADE,
                       null=True, blank=True, related_name='itineraries')
    llm_raw      = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_at = models.DateTimeField(null=True, blank=True)


class ItineraryDay(models.Model):
    itinerary  = models.ForeignKey(Itinerary, on_delete=models.CASCADE,
                     related_name='days')
    day_number = models.PositiveIntegerField()
    date       = models.DateField()
    location   = models.CharField(max_length=200)
    theme      = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['day_number']


class ItineraryActivity(models.Model):
    CATEGORY_CHOICES = [
        ('transport', 'Transport'),
        ('food', 'Food'),
        ('activity', 'Activity'),
        ('accommodation', 'Stay'),
        ('free', 'Free time'),
    ]

    day         = models.ForeignKey(ItineraryDay, on_delete=models.CASCADE,
                      related_name='activities')
    time_slot   = models.CharField(max_length=50)
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    place_id    = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['time_slot']


class PackingItem(models.Model):
    trip       = models.ForeignKey(Trip, on_delete=models.CASCADE,
                     related_name='packing_items')
    claimed_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                     null=True, blank=True, related_name='claimed_items')
    name       = models.CharField(max_length=200)
    category   = models.CharField(max_length=100, blank=True)
    is_packed  = models.BooleanField(default=False)

    def __str__(self):
        return self.name
