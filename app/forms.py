from django import forms
from django.core.exceptions import ValidationError
import re

class UserDataForm(forms.Form):
    name = forms.CharField(required=True)
    phone = forms.CharField(required=True)
    gender = forms.ChoiceField(choices=[('Male', 'Male'), ('Female', 'Female'),('Other', 'Other')])
    occupation = forms.CharField(required=False)
    education_level = forms.ChoiceField(choices=[
        ('None', 'None'),
        ('Primary', 'Primary'),
        ('Secondary', 'Secondary'),
        ('Tertiary', 'Tertiary')
    ])
    marital_status = forms.ChoiceField(choices=[
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed')
    ])
    income = forms.DecimalField(required=False)
    dependents = forms.IntegerField(required=False)
    age = forms.IntegerField()
    camera_image = forms.CharField(required=False)
    camera_image_name = forms.CharField(required=False)

  
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not (10 <= len(phone) <= 13):
            raise ValidationError('Phone number must be between 10 and 13 digits.')
        if not re.match(r'^\d+$', phone):
            raise ValidationError('Phone number must contain only digits.')
        return phone

    def clean_age(self):
        age = self.cleaned_data.get('age')
        if not (1 <= age <= 120):
            raise ValidationError('Age must be between 1 and 120.')
        return age

    def clean_occupation(self):
        age = self.cleaned_data.get('age')
        occupation = self.cleaned_data.get('occupation')
        if age is not None and age >= 18 and not occupation:
            raise ValidationError('Occupation is required for ages 18 and above.')
        return occupation

    def clean_education_level(self):
        age = self.cleaned_data.get('age')
        education_level = self.cleaned_data.get('education_level')
        
        if education_level is None:
            return education_level
        
        if education_level == 'Primary' and (age is not None and  (6 <= age <= 13)):
            raise ValidationError('Primary School education level is only applicable for ages 6-13.')
        elif education_level == 'Secondary' and (age is not None and  (14 >= age <= 20)):
            raise ValidationError('Secondary School education level is only applicable for ages 14-20.')
        elif education_level == 'Tertiary' and ( age is not None and age >= 18):
            raise ValidationError('Tertiary education level is only applicable for ages 18 and above.')
        
        return education_level

    def clean_marital_status(self):
        age = self.cleaned_data.get('age')
        marital_status = self.cleaned_data.get('marital_status')
        
        if marital_status is None :
            return marital_status
        
        if marital_status in ['Married', 'Divorced', 'Widowed'] and (age is None or age < 18):
            raise ValidationError('Marital status options Married, Divorced, and Widowed are only applicable for ages 18 and above.')
        
        return marital_status

    def clean_dependents(self):
        age = self.cleaned_data.get('age')
        dependents = self.cleaned_data.get('dependents')
        
        if age is not None and age >= 18 and dependents is None:
            raise ValidationError('Dependents are required for ages 18 and above.')
        
        return dependents

    def clean_income(self):
        income = self.cleaned_data.get('income')
        # if income is not None and not isinstance(income, (int, float)) or income < 0:
        #     raise ValidationError('Income must be numeric.')
        # if isinstance(income, (int, float)) and income < 0:
        #     raise ValidationError('Income must be a non-negative number.')
        if income is not None and income < 0:
            raise ValidationError('Income must be a non-negative number.')
        
        return income
