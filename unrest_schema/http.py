from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import ModelChoiceIteratorValue
from django.http import JsonResponse as _JsonResponse

class JsonEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, ModelChoiceIteratorValue):
            return obj.value
        if obj.__class__.__name__ in getattr(settings, 'UNREST_STRING_TYPES', []):
            return str(obj)
        return super().default(obj)

def JsonResponse(*args, **kwargs):
    kwargs['encoder'] = JsonEncoder
    return _JsonResponse(*args, **kwargs)