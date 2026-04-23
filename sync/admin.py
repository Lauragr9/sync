# Registers all Sync models with Django's admin interface, making them
# browsable and editable at /admin/ during development.

from django.contrib import admin
from .models import (Trip, TripMember, DestinationProposal,
                     Vote, Availability, Itinerary,
                     ItineraryDay, ItineraryActivity, PackingItem)

admin.site.register(Trip)
admin.site.register(TripMember)
admin.site.register(DestinationProposal)
admin.site.register(Vote)
admin.site.register(Availability)
admin.site.register(Itinerary)
admin.site.register(ItineraryDay)
admin.site.register(ItineraryActivity)
admin.site.register(PackingItem)