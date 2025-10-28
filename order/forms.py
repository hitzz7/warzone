# store/forms.py
from django import forms
from django.core.validators import RegexValidator
from .models import City

phone_validator = RegexValidator(
    regex=r'^\+?[0-9\-\s]{7,20}$',
    message="Enter a valid phone number (digits, spaces, dashes allowed)."
)

class CheckoutForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Full name', 'autocomplete': 'name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'input', 'placeholder': 'Email address', 'autocomplete': 'email'})
    )
    phone = forms.CharField(
        max_length=30,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Phone number', 'autocomplete': 'tel'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'input textarea', 'rows': 3, 'placeholder': 'Street address', 'autocomplete': 'street-address'})
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.order_by('name'),
        empty_label="Select city",
        widget=forms.Select(attrs={'class': 'input'})
    )
    landmark = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Landmark (optional)'})
    )
    applied_coupon = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.HiddenInput()
    )
