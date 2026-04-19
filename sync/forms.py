from django import forms
from .models import Trip, DestinationProposal 

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['name', 'description', 'departure_date', 'return_date', 'budget_range']
        widgets = {
            'departure_date': forms.DateInput(attrs={'type': 'date'}),
            'return_date': forms.DateInput(attrs={'type': 'date'}),
        }
class ProposalForm(forms.ModelForm):
    class Meta:
        model = DestinationProposal
        fields = ['city', 'country', 'notes', 'image_url']