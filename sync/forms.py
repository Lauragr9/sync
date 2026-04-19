from django import forms
from .models import Trip, DestinationProposal

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['name', 'description', 'departure_date', 'return_date', 'budget_range']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'departure_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'return_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'budget_range': forms.Select(attrs={'class': 'form-select'}),
        }

class ProposalForm(forms.ModelForm):
    class Meta:
        model = DestinationProposal
        fields = ['city', 'country', 'notes', 'image_url']
        widgets = {
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }