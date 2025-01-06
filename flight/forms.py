# your_app/forms.py
from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['content', 'time', 'picture', 'address']
        widgets = {
            'time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
