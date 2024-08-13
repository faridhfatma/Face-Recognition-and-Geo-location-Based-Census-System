from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinValueValidator, MaxValueValidator

# Define roles


class Role(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name

# Extend User model using a one-to-one link


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=100, default='')
    id_number = models.CharField(max_length=100, default='')
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

# Signal to automatically create/update UserProfile when User is created/updated
# python manage.py makemigrations app --empty --name populate_default_roles

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()


# class UserData(models.Model):
#     # Link UserData to a User
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     name = models.CharField(max_length=120, default='')
#     phone = models.CharField(max_length=100, default='')
#     age = models.IntegerField(default=0)
#     region = models.CharField(max_length=100, default='')
#     gender = models.CharField(max_length=10, choices=(
#         ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')), default='Other')
#     occupation = models.CharField(max_length=120, default='Other')
#     education_level = models.CharField(max_length=100, choices=(
#         ('None', 'None'), ('Primary', 'Primary'), ('Secondary', 'Secondary'), ('Tertiary', 'Tertiary')), default='None')
#     marital_status = models.CharField(max_length=50, choices=(('Single', 'Single'), (
#         'Married', 'Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed')), default='Single')
#     number_of_dependents = models.IntegerField(default=0)
#     income = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     image = models.ImageField(upload_to='user_images/')
#     city = models.CharField(max_length=100, blank=True, null=True)
#     country = models.CharField(max_length=100, blank=True, null=True)
#     location = models.CharField(max_length=255, blank=True, null=True)
#     device_ip = models.GenericIPAddressField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.name} ({self.region})"
#     def combined_region_info(self):
#         return f'{self.country}-{self.region}, {self.city}'

class UserData(models.Model):
    # Link UserData to a User
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=120, default='')
    phone = models.CharField(max_length=13, validators=[MaxLengthValidator(13)], default='')
    age = models.IntegerField(default=0)
    region = models.CharField(max_length=100, default='')
    gender = models.CharField(max_length=10, choices=(
        ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')), default='Other')
    occupation = models.CharField(max_length=120, default='Other')
    education_level = models.CharField(max_length=100, choices=(
        ('None', 'None'), ('Primary', 'Primary'), ('Secondary', 'Secondary'), ('Tertiary', 'Tertiary')), default='None')
    marital_status = models.CharField(max_length=50, choices=(
        ('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed')), default='Single')
    number_of_dependents = models.IntegerField(default=0)
    income = models.DecimalField(max_digits=100, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='user_images/')
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    device_ip = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.region})"

    def clean(self):
        super().clean()
        self.validate_age()
        self.validate_occupation()
        self.validate_education_level()
        self.validate_marital_status()
        self.validate_dependents()
        self.validate_income()

    def validate_age(self):
        if not (1 <= self.age <= 120):
            raise ValidationError({'age': 'Age must be between 1 and 120.'})

    def validate_occupation(self):
        if self.age >= 18 and not self.occupation:
            raise ValidationError({'occupation': 'Occupation is required for individuals aged 18 and above.'})

    def validate_education_level(self):
        if self.age < 6:
            if self.education_level != 'None':
                raise ValidationError({'education_level': 'Education level should be "None" for ages below 6.'})
        elif 6 <= self.age <= 14:
            if self.education_level != 'Primary':
                raise ValidationError({'education_level': 'Education level should be "Primary" for ages 6 to 14.'})
        elif 15 <= self.age <= 20:
            if self.education_level not in ['Primary', 'Secondary']:
                raise ValidationError({'education_level': 'Education level should be "Primary" or "Secondary" for ages 15 to 20.'})
        elif self.age > 20:
            if self.education_level not in ['Primary', 'Secondary', 'Tertiary']:
                raise ValidationError({'education_level': 'Education level should be "Primary", "Secondary", or "Tertiary" for ages above 20.'})

    def validate_marital_status(self):
        if self.age < 20 and self.marital_status not in ['Single']:
            raise ValidationError({'marital_status': 'Marital status should be "Single" for individuals under 20.'})
        if self.age >= 20 and self.marital_status not in ['Single', 'Married', 'Divorced', 'Widowed']:
            raise ValidationError({'marital_status': 'Marital status must be one of "Single", "Married", "Divorced", or "Widowed" for individuals aged 20 and above.'})

    def validate_dependents(self):
        if self.age < 18 and self.number_of_dependents != 0:
            raise ValidationError({'number_of_dependents': 'Number of dependents should be 0 for individuals under 18.'})
        if self.age >= 18 and self.number_of_dependents < 0:
            raise ValidationError({'number_of_dependents': 'Number of dependents must be a non-negative number for individuals 18 and above.'})

    def validate_income(self):
        if self.income < 0:
            raise ValidationError({'income': 'Income must be a non-negative number.'})

class FaceMetadata(models.Model):
    user_data = models.OneToOneField(UserData, on_delete=models.CASCADE)
    face_encoding = models.TextField()
