from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Min, Max, Avg, Count, Q
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
import logging
from django.db import transaction
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.core.files.base import ContentFile
import os
import base64
from django.core import serializers
from .forms import UserDataForm


from .models import Role, UserData, UserProfile, FaceMetadata
from .face_recognition import extract_face_metadata, compare_faces
from .location import get_geolocation
# Create your views here.

logger = logging.getLogger(__name__)


def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('login-redirect')
        else:
            messages.error(request, "Invalid username or password")
            return render(request, 'login.html', {})
    else:
        return render(request, 'login.html', {})


@login_required
def login_redirect(request):
    user_profile = request.user.userprofile
    if user_profile.role.name == 'Admin':
        return redirect('admin-dashboard')
    elif user_profile.role.name == 'Enumerator':
        return redirect('enumerator-dashboard')
    else:
        return redirect('login')


@login_required
def admin_view_dashboard(request):
    user_profile = request.user.userprofile
    if user_profile.role.name == 'Admin':
        data = fetch_dashboard_data()
        return render(request, 'admin/dashboard.html', data)
    else:
        # Instead of redirecting to the login page, consider showing a 403 Forbidden page or redirecting to a safe page
        return HttpResponseForbidden("You are not authorized to view this page.")


@login_required
def admin_view_enumerator(request):
    user_profile = request.user.userprofile
    if user_profile.role.name == 'Admin':
        if request.method == 'POST':
            # Extract form data
            first_name = request.POST.get('first_name')
            second_name = request.POST.get('second_name')
            username = request.POST.get('username')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            id_number = request.POST.get('id_number')
            password = '2024@Password'
            role_id = request.POST.get('role')

            print("Phone:", phone, "ID Number:", id_number)

            logger.warning("creating user")

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=second_name
                    )
                    # Create UserProfile
                    role = Role.objects.get(id=role_id)
                    logger.warning("User created now creating profile " +
                                   "Phone:"+phone+" ID Number:"+id_number+" Role:"+role.name)

                    UserProfile.objects.update_or_create(
                        user=user,
                        defaults={
                            'phone': phone,
                            'id_number': id_number,
                            'role_id': role_id
                        }
                    )

                messages.success(request, "New Staff created successfully")

            except IntegrityError as e:
                if 'username' in str(e):
                    messages.error(
                        request, "The username has already been taken. Please choose a different one.")
                else:
                    messages.error(
                        request, "An error occurred during staff account creation. Please try again. - {}".format(e))
            except Role.DoesNotExist:
                messages.error(request, "The selected role does not exist.")
            except Exception as e:
                messages.error(
                    request, "An unexpected error occurred: {}".format(e))

            data = fetch_enumerator_data()
            return render(request, 'admin/enumerator.html', data)
        else:
            data = fetch_enumerator_data()
            return render(request, 'admin/enumerator.html', data)
    else:
        # Instead of redirecting to the login page, consider showing a 403 Forbidden page or redirecting to a safe page
        return HttpResponseForbidden("You are not authorized to view this page.")


def fetch_dashboard_data():
    total_records = UserData.objects.count()
    age_range = UserData.objects.aggregate(
        min_age=Min('age'),
        max_age=Max('age')
    )
    # Set defaults for min_age and max_age if None
    age_range['min_age'] = age_range.get('min_age') or 0
    age_range['max_age'] = age_range.get('max_age') or 0

    max_income = UserData.objects.aggregate(Max('income'))['income__max'] or 0
    average_income = UserData.objects.aggregate(Avg('income'))[
        'income__avg'] or 0
    records_by_gender = UserData.objects.values('gender').annotate(
        total=Count('gender')).order_by('gender')
    records_by_marital_status = UserData.objects.values('marital_status').annotate(
        total=Count('marital_status')).order_by('marital_status')
    records_by_education_level = UserData.objects.values('education_level').annotate(
        total=Count('education_level')).order_by('education_level')
    records_grouped_by_region = UserData.objects.values(
        'region').annotate(total=Count('region')).order_by('region')

    # Calculating the percentage for each region
    for record in records_grouped_by_region:
        record['percentage'] = (
            record['total'] / total_records * 100) if total_records > 0 else 0

    user_data_records = UserData.objects.all()

    return {
        'total_records': total_records,
        'age_range': age_range,
        'max_income': max_income,
        'average_income': average_income,
        'records_by_gender': records_by_gender,
        'records_by_marital_status': records_by_marital_status,
        'records_by_education_level': records_by_education_level,
        'records_grouped_by_region': records_grouped_by_region,
        'user_data_records': user_data_records,
    }


def fetch_enumerator_data():
    # Fetch all users except superusers
    users = User.objects.filter(
        is_superuser=False).prefetch_related('userprofile')

    # Fetch all roles
    roles = Role.objects.all()

    # Pass users and roles to the template
    return {
        'users': users,
        'roles': roles,
    }


@login_required
def enumerator_view_dashboard(request):
    return save_user_data(request)


def fetch_enumerator_dashboard_data(request):
    # Initialize the context dictionary with empty defaults
    context = {'user_data': [], 'user_data_count': 0}

    # Attempt to get all user data records associated with the current user
    user_data_qs = UserData.objects.filter(user=request.user)

    # Update the context dictionary with actual data if exists
    context['user_data'] = user_data_qs
    context['user_data_count'] = user_data_qs.count()

    return context


@login_required
def enumerator_view_search(request):
    user_profile = request.user.userprofile
    if user_profile.role.name == 'Enumerator':
        if request.method == 'POST' and request.FILES['image']:
            image = request.FILES['image']

            # Temporarily save the image
            fs = FileSystemStorage()
            filename = fs.save(image.name, image)
            image_path = fs.path(filename)

            # Extract face data from the uploaded image
            uploaded_face_data = extract_face_metadata(image_path)

            # Attempt to find a matching user
            user_data = None
            for face_metadata in FaceMetadata.objects.all():
                # Assuming the comparison logic
                if compare_faces(face_metadata.face_encoding, uploaded_face_data):
                    user_data = face_metadata.user_data
                    break

            # Clean up: delete the temporarily stored image
            os.remove(image_path)
            return render(request, 'agent/search.html', {'user_data': user_data})
        else:
            return render(request, 'agent/search.html', {'user_data': None})
    else:
        # Instead of redirecting to the login page, consider showing a 403 Forbidden page or redirecting to a safe page
        return HttpResponseForbidden("You are not authorized to view this page.")



# def save_user_data(request):
#     user_profile = request.user.userprofile
  
#     if user_profile.role.name == 'Enumerator':
#         if request.method == 'POST':
#             user = request.user
#             name = request.POST['name']
#             phone = request.POST['phone']
#             gender = request.POST['gender']
#             occupation = request.POST['occupation']
#             education_level = request.POST['education_level']
#             marital_status = request.POST['marital_status']
#             income = request.POST['income']
#             dependents = request.POST['dependents']
#             age = request.POST['age']
#             # image = request.FILES['image']
#             camera_image = request.POST['camera_image']
#             camera_image_name = request.POST['camera_image_name']
            
            
#             # Ensure all required fields are provided
#             required_fields = ['name', 'phone', 'age', 'camera_image']
#             for field in required_fields:
#                 if not form_data.get(field):
#                     messages.error(request, f"{field.replace('_', ' ').capitalize()} is required.")
#                     return redirect('enumerator-dashboard')

#             try:
#             # Process the image file
#                 fs = FileSystemStorage()

#                 if 'image' in request.FILES and request.FILES['image']:
#                     image = request.FILES['image']
#                     filename = fs.save(image.name, image)
#                 elif camera_image:
                
#                     camera_image_binary = base64.b64decode(camera_image.split(',')[1])
#                     django_file = ContentFile(camera_image_binary, name=camera_image_name)
#                     filename = fs.save(camera_image_name, django_file)
                
#                 image_url = fs.url(filename)

#                 # Getting the absolute filesystem path of the saved image
#                 image_abs_path = os.path.join(settings.MEDIA_ROOT, filename)
#                 face_data = extract_face_metadata(image_abs_path)
                
#                 user_data = None

#                 # Attempt to find a matching user
                
#                 for face_meta_data in FaceMetadata.objects.all():
#                     # Assuming the comparison logic
#                     if compare_faces(face_meta_data.face_encoding, face_data):
#                         user_data = face_meta_data.user_data
#                         break
#                 if user_data:
#                     # Clean up: delete the temporarily stored image
#                     os.remove(image_abs_path)
#                     messages.error(
#                         request, "An individual with the same face exists")
#                     data = fetch_enumerator_dashboard_data(request)
#                     request.session['modal_show'] = True 
#                     request.session['userss_data'] = serializers.serialize('json', [user_data]) 
#                     return redirect('enumerator-dashboard')



#                 if face_data is None:
#                     messages.error(
#                         request, "Invalid image. Your image must have only one clear face.")
#                     # return JsonResponse({'success': False, 'message': 'Invalid image. Your image must have only one clear face'})
#                 else:
#                     # Create UserData instance

#                     try:

#                         geolocation_data = get_geolocation()

#                         if geolocation_data is None:
#                             os.remove(image_abs_path)
#                             messages.error(request, "Unable to retrieve geolocation data.")
#                             return redirect('enumerator-dashboard')
                      

#                         city = geolocation_data.get('city', '')
#                         country = geolocation_data.get('country', '')
#                         location = geolocation_data.get('loc', '')
#                         device_ip = geolocation_data.get('ip', '')
#                         region = geolocation_data.get('region', '')

#                         data = UserData.objects.create(
#                             user=user,
#                             name=name,
#                             age=age,
#                             phone=phone,
#                             region=region,
#                             gender=gender,
#                             occupation=occupation,
#                             education_level=education_level,
#                             marital_status=marital_status,
#                             income=income,
#                             number_of_dependents=dependents,
#                             image=image_url,
#                             city=city,
#                             country=country,
#                             location=location,
#                             device_ip=device_ip
#                         )

#                         FaceMetadata.objects.create(
#                             user_data=data,
#                             face_encoding=face_data
#                         )

#                         messages.success(request, "New enumeration saved successfully")
#                         # return JsonResponse({'success': True, 'message': 'User Registered Succesfully'})
#                         return redirect('enumerator-dashboard')

#                     except Exception as e:
#                         os.remove(image_abs_path)
#                         messages.error(request,str(e))

#             except Exception as e:  # Catch general exceptions during image processing
#              os.remove(image_abs_path)
#              messages.error(request,"The image you have uploaded is not clear enough or the face cannot be seen.")

#         user_data_serialized = request.session.pop('userss_data', None)
#         if user_data_serialized:
#           userss_data = serializers.deserialize('json', user_data_serialized)
#           userss_data = list(userss_data)[0].object  # Get the actual UserData object
#         else:
#           userss_data = None
#         modal_show = request.session.pop('modal_show', False)

#         data = fetch_enumerator_dashboard_data(request)
#         return render(request, 'agent/dashboard.html',  { 'userss_data': userss_data, 'modal_show':modal_show,**data})
#     else:
#         # Instead of redirecting to the login page, consider showing a 403 Forbidden page or redirecting to a safe page
#         return HttpResponseForbidden("You are not authorized to view this page.")

def save_user_data(request):
    user_profile = request.user.userprofile

    if user_profile.role.name == 'Enumerator':
        form = UserDataForm(request.POST or None, request.FILES or None)
        
        if request.method == 'POST':
            if form.is_valid():
                # Form is valid, process the data
                name = form.cleaned_data['name']
                phone = form.cleaned_data['phone']
                gender = form.cleaned_data['gender']
                occupation = form.cleaned_data['occupation']
                education_level = form.cleaned_data['education_level']
                marital_status = form.cleaned_data['marital_status']
                income = form.cleaned_data['income']
                dependents = form.cleaned_data['dependents']
                age = form.cleaned_data['age']
                camera_image = form.cleaned_data.get('camera_image', None)
                camera_image_name = form.cleaned_data.get('camera_image_name', None)

                try:
                    # Validate image inputs
                    if not camera_image and not 'image' in request.FILES:
                        messages.error(request, "You must add an image")
                        return redirect('enumerator-dashboard')

                    fs = FileSystemStorage()
                    filename = None
                    image_url = None

                    # Handle image from the request
                    if 'image' in request.FILES and request.FILES['image']:
                        image = request.FILES['image']
                        filename = fs.save(image.name, image)
                    elif camera_image:
                        camera_image_binary = base64.b64decode(camera_image.split(',')[1])
                        django_file = ContentFile(camera_image_binary, name=camera_image_name)
                        filename = fs.save(camera_image_name, django_file)

                    if filename:
                        image_url = fs.url(filename)

                        # Get the absolute path of the saved image
                        image_abs_path = os.path.join(settings.MEDIA_ROOT, filename)
                        face_data = extract_face_metadata(image_abs_path)

                        if face_data is None:
                            messages.error(request, "Invalid image. Your image must have only one clear face.")
                            return redirect('enumerator-dashboard')

                        # Attempt to find a matching user
                        user_data = None
                        for face_meta_data in FaceMetadata.objects.all():
                            if compare_faces(face_meta_data.face_encoding, face_data):
                                user_data = face_meta_data.user_data
                                break

                        if user_data:
                            os.remove(image_abs_path)
                            messages.error(request, "An individual with the same face exists.")
                            request.session['modal_show'] = True
                            request.session['userss_data'] = serializers.serialize('json', [user_data])
                            return redirect('enumerator-dashboard')

                        # Create UserData instance and validate
                        geolocation_data = get_geolocation()

                        if geolocation_data is None:
                            os.remove(image_abs_path)
                            messages.error(request, "Unable to retrieve geolocation data.")
                            return redirect('enumerator-dashboard')

                        city = geolocation_data.get('city', '')
                        country = geolocation_data.get('country', '')
                        location = geolocation_data.get('loc', '')
                        device_ip = geolocation_data.get('ip', '')
                        region = geolocation_data.get('region', '')

                        user_data = UserData(
                            user=request.user,
                            name=name,
                            age=age,
                            phone=phone,
                            region=region,
                            gender=gender,
                            occupation=occupation,
                            education_level=education_level,
                            marital_status=marital_status,
                            income=income,
                            number_of_dependents=dependents,
                            image=image_url,
                            city=city,
                            country=country,
                            location=location,
                            device_ip=device_ip
                        )

                        try:
                            user_data.clean()  # Trigger model validation
                            user_data.save()  # Save the UserData instance

                            FaceMetadata.objects.create(
                                user_data=user_data,
                                face_encoding=face_data
                            )

                            messages.success(request, "New enumeration saved successfully")
                            return redirect('enumerator-dashboard')

                        except ValidationError as e:
                            messages.error(request, f"Validation errors occurred: {str(e.message_dict)}")
                        except Exception as e:
                            messages.error(request, f"Error: {str(e)}")

                        finally:
                            # Ensure image is deleted even if an error occurs
                            if os.path.exists(image_abs_path):
                                os.remove(image_abs_path)

                except Exception as e:
                    messages.error(request, f"Error: {str(e)}")

            else:
                # If the form is invalid, show errors
                messages.error(request, "Please correct the errors below.")

        user_data_serialized = request.session.pop('userss_data', None)
        if user_data_serialized:
            userss_data = serializers.deserialize('json', user_data_serialized)
            userss_data = list(userss_data)[0].object
        else:
            userss_data = None

        modal_show = request.session.pop('modal_show', False)
        data = fetch_enumerator_dashboard_data(request)
        return render(request, 'agent/dashboard.html', {
            'form': form,
            'userss_data': userss_data,
            'modal_show': modal_show,
            **data
        })

    else:
        return HttpResponseForbidden("You are not authorized to view this page.")
  
def clear_modal_session(request):
    if request.method == 'POST':
        request.session.pop('userss_data', None)
        request.session.pop('modal_show', None)
        
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def enumerator_delete_enumeration_record(request, record_id):
    record = get_object_or_404(UserData, pk=record_id)
    # Check if the user is allowed to delete the record
    if request.user.is_authenticated and request.user == record.user:
        # If the object has an image field and an image is associated
        if record.image:
            # Construct the full file path
            filename = record.image.name.split('/')[-1]
            image_path = os.path.join(settings.MEDIA_ROOT, filename)
            # Delete the file if it exists
            if os.path.isfile(image_path):
                os.remove(image_path)
        record.delete()
        messages.success(request, 'Record deleted successfully.')
    else:
        messages.error(
            request, 'You do not have permission to delete this record.')
    return redirect(reverse('enumerator-dashboard'))


@login_required
def admin_delete_enumeration_record(request, record_id):
    record = get_object_or_404(UserData, pk=record_id)
    if request.user.is_authenticated:
        # If the object has an image field and an image is associated
        if record.image:
            # Construct the full file path
            filename = record.image.name.split('/')[-1]
            image_path = os.path.join(settings.MEDIA_ROOT, filename)
            # Delete the file if it exists
            if os.path.isfile(image_path):
                os.remove(image_path)
        record.delete()
        messages.success(request, 'Record deleted successfully.')
    else:
        messages.error(
            request, 'You do not have permission to delete this record.')
    return redirect(reverse('admin-dashboard'))


def logout_view(request):
    logout(request)
    return redirect('login')
