# loosely based on: https://github.com/Cahersan/django-schemulator
from collections import OrderedDict
from django import forms
from django.db.models.fields.files import ImageFieldFile

# django keywords to rjsf keywords
KEYWORDS = {
  #Base keywords
  "label": "title",
  "help_text": "description",
  "initial": "default",
  "required": "required",

  #String type-specific keywords
  "max_length": "maxLength",
  "min_length": "minLength",

  #Numerical type-specific keywords
  "min_value": "minimum",
  "max_value": "maximum",
}

# django fields to rjsf types
FIELD_TO_TYPE = {
  'IntegerField': 'integer',
  'BooleanField': 'boolean',
  'TypedChoiceField': '',
  'ModelChoiceField': 'integer',
  'JSONField': 'object',
}

# django fields to rjsf formats
FIELD_TO_FORMAT = {
  'EmailField': 'email',
  'DateTimeField': 'date-time',
}


def field_to_schema(field):
  field_type = field.__class__.__name__
  schema = {
    'type': FIELD_TO_TYPE.get(field_type, 'string'),
  }

  if schema['type'] == 'object':
    schema['properties'] = {}

  if not schema['type']:
    #currently only supported for TypedChoiceField
    sample_value = field.coerce('1')
    if isinstance(sample_value, (int, float)):
      schema['type'] = 'integer'
    elif isinstance(sample_value, bool):
      schema['type'] = 'boolean'
    else:
      schema['type'] = 'string'

  if field_type in FIELD_TO_FORMAT:
    schema['format'] = FIELD_TO_FORMAT.get(field_type, None)

  # Setup of JSON Schema keywords
  for (field_attr, schema_attr) in KEYWORDS.items():
    if hasattr(field, field_attr):
      schema[schema_attr] = getattr(field, field_attr)

  # choices needs to be two attrs, so handle it separately
  if hasattr(field, 'choices'):
    optional = not schema.get('required')
    schema['enum'] = [a for a, b in field.choices]
    schema['enumNames'] = [b for a, b in field.choices]
    if not optional and not schema['enum'][0]:
      schema['enum'] = schema['enum'][1:]
      schema['enumNames'] = schema['enumNames'][1:]

  # RJSF doesn't like minLength = null
  if schema.get('minLength', 0) is None:
    schema.pop('minLength')

  if field_type == 'ImageField':
    # RJSF confuses length of file and length of filename, eg "megapixel.png" is 1e6 characters long
    schema.pop('maxLength', None)
    # RJSF is confusde by default None on file field
    schema.pop('default', None)

  if field_type == 'ModelMultipleChoiceField':
    schema['type'] = 'array'
    schema['items'] = {
      'type': 'integer',
      'enum': schema.pop('enum'),
      'enumNames': schema.pop('enumNames'),
    }

  for field_attr in ['maxLength', 'title', 'maximum', 'minimum', 'default']:
    if schema.get(field_attr, '') is None:
      schema.pop(field_attr)

  # Set __django_form_field_cls keyword
  schema['__django_form_field_cls'] = field_type
  schema['__widget'] = field.widget.__class__.__name__
  if isinstance(field.widget, forms.PasswordInput):
    schema['format'] = 'password'
  if isinstance(field.widget, forms.HiddenInput):
    schema['format'] = 'hidden'

  return schema


def get_default_value(form, name):
  if form.fields[name].__class__.__name__ == 'ModelChoiceField':
    return getattr(form.instance, name + '_id')
  value = getattr(form.instance, name)
  if isinstance(value, ImageFieldFile):
    if not value:
      return
    else:
      value = value.url
  if hasattr(value, 'pk'):
    value = value.pk
  if form.fields[name].__class__.__name__ == 'ModelMultipleChoiceField':
    value = [obj.id for obj in value.all()]
  return value


def form_to_schema(form):
  schema = {
    'type': 'object',
    'properties': OrderedDict([
      (name, field_to_schema(field))
      for (name, field) in form.fields.items()
    ]),
    'required': []
  }

  for name, field in schema['properties'].items():
    if field.pop('required', None):
      schema['required'].append(name)
    if getattr(form, 'instance', None):
      if hasattr(form.instance, name) and getattr(form.instance, name) != None:
        value = get_default_value(form, name)
        if value != None:
          schema['properties'][name]['default'] = value

  if hasattr(form, 'form_title'):
    schema['title'] = form.form_title

  return schema
