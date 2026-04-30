from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import StudentProfile, FeePayment, Department


class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
    )
    last_name = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all().order_by('name'),
        required=True,
        empty_label='-- Select Your Department --',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    matric_number = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CSC/2020/001'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_matric_number(self):
        matric = self.cleaned_data.get('matric_number', '').strip()
        if not matric:
            raise forms.ValidationError('Matric number is required.')
        if StudentProfile.objects.filter(matric_number=matric).exists():
            raise forms.ValidationError('This matric number is already registered.')
        return matric

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Email is required.')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already registered.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username


class StudentProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = StudentProfile
        fields = ['phone', 'date_of_birth', 'address', 'profile_picture']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Home Address'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already in use by another account.')
        return email

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            if hasattr(picture, 'size') and picture.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Profile picture must be under 2MB.')
            allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if hasattr(picture, 'content_type') and picture.content_type not in allowed:
                raise forms.ValidationError('Only JPG, PNG, GIF or WEBP images are allowed.')
        return picture

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.profile_completed = True
        if commit:
            with transaction.atomic():
                if self.user:
                    self.user.first_name = self.cleaned_data['first_name']
                    self.user.last_name = self.cleaned_data['last_name']
                    self.user.email = self.cleaned_data['email']
                    self.user.save()
                profile.save()
        return profile


class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeePayment
        fields = ['amount_paid', 'bank_name', 'transaction_reference', 'payment_date', 'receipt']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount Paid (₦)'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. First Bank'}),
            'transaction_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction Reference / RRR'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }

    def __init__(self, *args, **kwargs):
        self.fee = kwargs.pop('fee', None)
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        if self.fee:
            self.fields['amount_paid'].initial = self.fee.total_amount()

    def clean_receipt(self):
        receipt = self.cleaned_data.get('receipt')
        if receipt:
            if receipt.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must not exceed 5MB.')
            allowed = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
            if hasattr(receipt, 'content_type') and receipt.content_type not in allowed:
                raise forms.ValidationError('Only PDF, JPG, and PNG files are allowed.')
        return receipt