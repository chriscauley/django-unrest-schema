from django.http import Http404
from django.contrib import admin
from django.contrib.auth import get_user_model
from django import forms

import distutils.util
import json
import re

from .pagination import paginate
from .http import JsonResponse
from .utils import form_to_schema, get_default_value

FORMS = {}

def clean_form_name(form_name):
    form_name = form_name
    form_name = re.sub(r'(?<!^)(?=[A-Z])', '-', form_name).lower()
    return re.sub(r'-form$', '', form_name)


def register(form, form_name=None):
    if isinstance(form, str):
        # register is being used as a decorator and args are curried and reversed
        return lambda actual_form: register(actual_form, form_name=form)
    form_name = clean_form_name(form_name or form.__name__)
    old_form = FORMS.get(form_name, form)
    if repr(form) != repr(old_form):
        e = f"Form with name {form_name} has already been registered.\nOld: {old_form}\nNew:{form}"
        raise ValueError(e)

    FORMS[form_name] = form
    return form


def unregister(form_name):
    FORMS.pop(clean_form_name(form_name), None)


def schema_form(request, form_class, object_id=None, method=None, content_type=None, model=None):
    if type(form_class) == str:
        if form_class.endswith('-form') or form_class.endswith('Form'):
            raise ValueError('Schema forms should no longer end in "Form" or "-form"')
        if not form_class in FORMS:
            keys = '\n'.join(FORMS.keys())
            raise Http404(f"Form with name {form_class} does not exist in: \n{keys}")
        form_class = FORMS[form_class]
    method = method or request.method
    content_type = content_type or request.headers.get('Content-Type', None)
    _meta  = getattr(form_class, 'Meta', object())
    if hasattr(_meta, 'model'):
        model = _meta.model
    kwargs = {}
    if object_id:
        kwargs['instance'] = model.objects.get(id=object_id)
    if getattr(_meta, 'login_required', None) and not request.user.is_authenticated:
        print("DEPRECATION WARNING: user form.user_can_METHOD = 'AUTH' instead of meta option.")
        return JsonResponse({'error': 'You must be logged in to do this'}, status=403)
    if getattr(form_class, 'user_can_GET', None) == 'SELF' or getattr(form_class, 'user_can_PUT', None) == 'SELF':
        kwargs['instance'] = request.user

    def check_permission(permission):
        if request.user.is_superuser:
            return True
        instance = kwargs.get('instance')
        f = getattr(form_class, 'user_can_' + permission, None)
        if f == 'SELF':
            return request.user == instance
        if f == 'OWN':
            return request.user == instance.user
        if f == 'ALL':
            return True
        if f == 'AUTH':
            return request.user.is_authenticated
        if f == 'ANY':
            print("DEPRECATION WARNING: user_can_METHOD='ANY' should be 'ALL' or 'AUTH'")
            return True
        return f and f(instance, request.user)

    if request.method == "POST" or request.method == "PUT":
        # POST/PUT /api/schema/MODEL/ or /api/schema/MODEL/PK/
        if kwargs.get('instance') and not check_permission('PUT'):
            return JsonResponse({'error': 'You cannot edit this resource.'}, status=403)
        if not kwargs.get('instance') and not check_permission('POST'):
            return JsonResponse({'error': 'You cannot create this resource.'}, status=403)
        if content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8') or "{}")
            form = form_class(data, **kwargs)
        else:
            form = form_class(request.POST, request.FILES, **kwargs)

        form.request = request
        if form.is_valid():
            instance = form.save()
            data = {}
            if instance:
                data = {'id': instance.id, 'name': str(instance)}
            return JsonResponse(data)
        errors = { k: v[0] for k, v in form.errors.get_json_data().items()}
        return JsonResponse({'errors': errors}, status=400)

    if request.method == "DELETE":
        # DELETE /api/schema/MODEL/ or /api/schema/MODEL/PK/
        if kwargs.get('instance') and check_permission('DELETE'):
            kwargs['instance'].delete()
            return JsonResponse({})
        return JsonResponse({'error': 'You cannot edit this resource.'}, status=403)

    if kwargs.get('instance') and not check_permission('GET'):
        return JsonResponse({'error': 'You do not have access to this resource'}, status=403)

    if request.GET.get('schema'):
        # /api/schema/MODEL/?schema=1 or /api/schema/MODEL/PK/?schema=1
        schema = form_to_schema(form_class(**kwargs))
        return JsonResponse({'schema': schema})

    def process(instance):
        out = { 'id': instance.id }
        form = form_class(instance=instance)
        for field_name in form.Meta.fields:
            out[field_name] = get_default_value(form, field_name)
        for field_name in getattr(form, 'readonly_fields', []):
            # TODO should this be on the model or the form?
            out[field_name] = getattr(instance, field_name)
        return out

    if kwargs.get('instance'):
        # /api/schema/MODEL/PK/
        return JsonResponse(process(form_class(**kwargs).instance))

    # defaults to /api/schema/MODEL/
    if not check_permission('LIST'):
        return JsonResponse({'error': 'You do not have access to this resource'}, status=403)
    if model.__name__ == 'User':
        model = get_user_model()

    form = form_class()
    form.request = request
    if hasattr(form, 'get_queryset'):
        queryset = form.get_queryset(request)
    else:
        queryset = model.objects.all()
    # TODO this should be explicit like form_class.filter_fields or similar
    for field_name in form_class.Meta.fields:
        if field_name in request.GET:
            queryset = queryset.filter(**{field_name: request.GET[field_name]})
    for field_name in getattr(form_class, 'filter_fields', None) or []:
        if field_name in request.GET:
            value = request.GET[field_name]
            if field_name.endswith('__isnull'):
                value = bool(distutils.util.strtobool(value))
            queryset = queryset.filter(**{field_name: value})
    response = JsonResponse(paginate(queryset, process=process, query_dict=request.GET))
    return response


def get_model_and_admin(app_label, model_name):
    for model, admin_options in admin.site._registry.items():
        if model._meta.app_label == app_label and model._meta.model_name == model_name:
            return [model, admin_options]


def admin_form(request, app_label='', model_name='', object_id=None):
    [_model, admin] = get_model_and_admin(app_label, model_name)
    form = admin.get_form(request, None, fields=None)
    _fields = [*form.base_fields, *admin.get_readonly_fields(request, None)]
    class Form(forms.ModelForm):
        class Meta:
            model = _model
            fields = _fields
    return schema_form(request, Form, object_id=object_id, model=_model)


def admin_index(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'You do not have access to this resource'}, status=403)
    apps = {}
    for model, admin_options in admin.site._registry.items():
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        if app_label not in apps:
            apps[app_label] = {
                'app_label': app_label,
                'models': [],
            }
        apps[app_label]['models'].append({
            'verbose': model._meta.verbose_name,
            'verbose_plural': model._meta.verbose_name_plural,
            'app_label': app_label,
            'model_name': model_name,
            'count': model.objects.all().count(),
        })
    return JsonResponse({ 'apps': apps })
