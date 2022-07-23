from setuptools import setup, find_packages

setup(
  name = 'django-unrest-schema',
  packages = find_packages(),
  version = '0.0.2',
  description = 'A library for serving django forms using json schema and a restful api.',
  long_description="",
  long_description_content_type="text/markdown",
  author = 'Chris Cauley',
  author_email = 'chris@lablackey.com',
  url = 'https://github.com/chriscauley/django-unrest-schema',
  keywords = ['utils', 'django', 'jsonschema'],
  license = 'MIT',
  include_package_data = True,
  install_requires = [
    'django>=4.0.0',
  ]
)
