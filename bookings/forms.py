from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Booking

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('phone_number',)

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label='Phone Number', widget=forms.TextInput(attrs={'placeholder': 'Enter Phone Number', 'class': 'cyber-input'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'class': 'cyber-input'}))

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['screen', 'date', 'time_slot']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
