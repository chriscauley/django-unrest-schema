# Django Unrest Schema

A library for building a [jsonschema](https://json-schema.org/) API on top of django's forms. Currently I use this with my [@unrest/vue-form](https://github.com/chriscauley/unrest-vue-form/) to directly convert django forms into vue forms with no additional configuration.

## Usage

Register any form using the `unrest_schema.register` decorator.

``` python
from django import forms
import unrest_schema

from myapp.models import MyModel

@unrest_schema.register
class MyModelForm(forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ('field1', 'field2')
```

Import `forms.py` and include `unrest_schema.urls` in your main urls.py file.

``` python
from django.urls import include, path

import mysite.forms # noqa

urlpatterns = [
    # insert all other urls here
    path('', include('unrest_schema.urls')),
]
```

That's it! Your form will now be accessible via `/api/schema/MODEL_NAME/` where MODEL_NAME is the slugified version of the form name minus "form" (so MyModelForm turns into "my-model"). Note that by default form is only accessible by an authenticaed superuser (see permission section below for more details).

* GET `/api/schema/my-model/?schema=true` - Returns the jsonschema describing this form

* GET `/api/schema/my-model/1/?schema=true` - Returns the jsonschema with initial values matching object with id=1

* GET `/api/schema/my-model/` - List view (see pagination for more details)

* GET `/api/schema/my-model/1/` - Returns only the object with id=1

* POST `/api/schema/my-model/` - Create a new object

* PUT `/api/schema/my-model/1/` - Update object with id=1

* DELETE `/api/schema/my-model/1/` - Delete object with id=1

### Permissions

By default, all methods are restricted to superusers. To extend the permissions add `user_can_METHOD` properties/methods to the form class.

``` python
@unrest_schema.register
class MyModelForm(forms.ModelForm):
    user_can_GET = 'ALL'
    user_can_LIST = 'ALL'
    user_can_POST = 'AUTH'
    user_can_DELETE = 'OWN'
    def user_can_PUT(instance, user):
        return instance.user_is_owner(user)
    class Meta:
        model = MyModel
        fields = ('field1', 'field2', 'user')
```

The possible values for these properties are:

* `None` (or unset) - Superusers only.

* `"ALL"` - Anyone (including anonymous users).

* `"AUTH"` - Any authenticated user.

* `"SELF"` - Form instance must be equal to `request.user` (eg a user profile form)

* `"OWN"` - User owns object via `form.instance.user == request.user`

* method - Behavior can be fully customized by adding a function like `def user_can_GET(instance, user)` which should return true (user can access form) or false (will throw 403 error).

### Pagination

The list view returns the paginated items from the database. Adding the query parameters `page` (1-indexed) and `per_page` (default 10) will adjust which items are sent back. In addition to the items, the response will return the following pagination information.

``` json
{
  "items": [...],
  "pages": 26,
  "page": 1,
  "total": 258,
  "next_page": 2,
  "prev_page": null,
}
```

### Advanced configuration

* This library is designed to work with django's form library, so you can customize your form like you would normally. If you need an additional field added or if something doesn't work out of the box, please open an issue.

* As a convenience the request object is attached to the form after instantiation. To access the user during `MyForm.save` use `form.request.user`.

* Some python classes will cause django's json encoder to throw an error. You can specify `UNREST_STRING_TYPES = ["ULID"]` in your settings.py and this library will cast those fields as strings. Here `"ULID"` is the result of `value.__class__.__name__`.