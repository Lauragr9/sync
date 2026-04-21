from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Availability, DestinationProposal, Trip


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username'}),
        error_messages={'required': 'Enter your username.'},
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
        error_messages={'required': 'Enter your password.'},
    )

    def clean(self):
        # Use backend-authenticated checks to return precise login failure messages.
        cleaned_data = super(AuthenticationForm, self).clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not username or not password:
            return cleaned_data

        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
        except user_model.DoesNotExist:
            raise ValidationError('No account found with that username.')

        if not user.check_password(password):
            raise ValidationError('Incorrect password.')

        self.confirm_login_allowed(user)
        self.user_cache = user
        return cleaned_data


class SignUpForm(UserCreationForm):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username'}),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text='Use at least 8 characters with uppercase, lowercase, a number, and a special character.',
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username',)

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        checks = [
            (len(password) >= 8, 'Password must be at least 8 characters long.'),
            (re.search(r'[A-Z]', password), 'Password must include at least one uppercase letter.'),
            (re.search(r'[a-z]', password), 'Password must include at least one lowercase letter.'),
            (re.search(r'\d', password), 'Password must include at least one number.'),
            (re.search(r'[^A-Za-z0-9]', password), 'Password must include at least one special character.'),
        ]
        errors = [message for ok, message in checks if not ok]
        if errors:
            raise ValidationError(errors)
        return password


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate().isoformat()
        self.fields['departure_date'].widget.attrs['min'] = today
        self.fields['return_date'].widget.attrs['min'] = today

        if self.instance and self.instance.departure_date:
            self.fields['return_date'].widget.attrs['min'] = max(
                timezone.localdate(),
                self.instance.departure_date,
            ).isoformat()

    def clean(self):
        # Mirror date rules server-side so manual or tampered inputs are rejected.
        cleaned_data = super().clean()
        departure_date = cleaned_data.get('departure_date')
        return_date = cleaned_data.get('return_date')
        today = timezone.localdate()

        if departure_date and departure_date < today and (not self.instance.pk or departure_date != self.instance.departure_date):
            self.add_error('departure_date', 'Departure date cannot be in the past.')

        if return_date and return_date < today and (not self.instance.pk or return_date != self.instance.return_date):
            self.add_error('return_date', 'Return date cannot be in the past.')

        if departure_date and return_date and return_date <= departure_date:
            self.add_error('return_date', 'Return date must be after the departure date.')

        return cleaned_data


class AvailabilityForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        error_messages={'required': 'Choose a date.'},
    )
    status = forms.ChoiceField(
        choices=Availability.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Choose an availability status.'},
    )

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop('trip', None)
        super().__init__(*args, **kwargs)

        today = timezone.localdate()
        self.fields['date'].widget.attrs['min'] = today.isoformat()

        if self.trip and self.trip.departure_date:
            self.fields['date'].widget.attrs['min'] = max(today, self.trip.departure_date).isoformat()
        if self.trip and self.trip.return_date:
            self.fields['date'].widget.attrs['max'] = self.trip.return_date.isoformat()

    def clean_date(self):
        # Availability entries must be future/present dates inside the trip window.
        selected_date = self.cleaned_data['date']
        today = timezone.localdate()

        if selected_date < today:
            raise ValidationError('Past dates are not allowed.')

        if not self.trip or not self.trip.departure_date or not self.trip.return_date:
            raise ValidationError('Set the trip departure and return dates before adding availability.')

        if selected_date < self.trip.departure_date or selected_date > self.trip.return_date:
            raise ValidationError('Choose a date within the trip dates.')

        return selected_date

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