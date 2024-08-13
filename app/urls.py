from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('login', views.login_user, name='login'),
    path('login/redirect', views.login_redirect, name='login-redirect'),
    path('admin', views.admin_view_dashboard, name='admin-dashboard'),
    path('admin/enumerator', views.admin_view_enumerator, name='admin-enumerator'),
    path('enumerator', views.enumerator_view_dashboard,
         name='enumerator-dashboard'),
    path('enumerator/search', views.enumerator_view_search,
         name='enumerator-search'),
    path('logout', views.logout_view, name='logout'),
    path('enumeration/delete/data/<int:record_id>/',
         views.enumerator_delete_enumeration_record, name='enumerator_delete_enumeration_record'),
    path('admin/delete/data/<int:record_id>/',
         views.admin_delete_enumeration_record, name='admin-delete-enumeration'),
    path('enumeration/save',
         views.save_user_data, name='enum-save'),
    path('clear-modal-session/', views.clear_modal_session, name='clear-modal-session'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
