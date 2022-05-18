from django.urls import path

from .views import schema_form, admin_index, admin_form

urlpatterns = [
    path('api/admin/', admin_index),
    path('api/admin/<app_label>/<model_name>/', admin_form),
    path('api/admin/<app_label>/<model_name>/<object_id>/', admin_form),
    path('api/schema/<form_class>/', schema_form),
    path('api/schema/<form_class>/<object_id>/', schema_form),
]