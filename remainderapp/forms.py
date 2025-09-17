from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import os 


class RegisterForm(forms.ModelForm):
    username = forms.CharField(label='username',max_length=100,required=True)
    email = forms.EmailField(label='email',max_length=100,required=True)
    password = forms.CharField(label='password',min_length=8,required=True)
    confirm_password = forms.CharField(label='confirm_password',min_length=8,required=True)

    class Meta:
        model = User 
        fields = ['username','email','password']

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("password does not match")



class AddDoctorForm(forms.Form):
    file = forms.FileField(
        label="Choose file",
        help_text="Upload .csv, .xls or .xlsx",
        widget=forms.FileInput(attrs={'accept':'.csv, .xls, .xlsx'})
    )

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if not f:
            raise forms.ValidationError("No file uploaded.")
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ['.csv', '.xls', '.xlsx']:
            raise forms.ValidationError("Unsupported file extension. Use .csv, .xls or .xlsx.")
        # Optional: limit file size (example 5MB)
        max_size = 5 * 1024 * 1024
        if f.size > max_size:
            raise forms.ValidationError("File too large (max 5MB).")
        return f


class LoginForm(forms.Form):
    username = forms.CharField(label="username",max_length=100, required=True)
    password = forms.CharField(label="password",min_length=8,required=True)

    def clean(self):
        cleaned_data= super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password:
            user = authenticate(username=username , password=password)
            if user is None:
                raise forms.ValidationError("Account not Found!")
                

class ContactForm(forms.Form):
    subject = forms.CharField(max_length=200, required=True, label="Subject")
    message = forms.CharField(widget=forms.Textarea, required=True, label="Message")