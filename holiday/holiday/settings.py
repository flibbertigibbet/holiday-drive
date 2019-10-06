"""
Django settings for holiday project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

### ORGANIZATION SETTINGS
# Name of organization hosting holiday drive, used in templates
ORGANIZATION_NAME = 'Test Organization'
# Name of the holiday drive, used in templates
SITE_NAME = '{org} Holiday Drive'.format(org=ORGANIZATION_NAME)
# Email address used for sending emails to donors
ORGANIZATION_EMAIL = 'test@example.com'
# Email address provided to donors in case they have questions
DONOR_CONTACT_EMAIL = 'test@example.com'
# Links to main organization site
ORGANIZATION_MAIN_SITE = 'http://example.com'
# Where donors can make a cash donation instead
ORGANIZATION_CASH_DONATION_LINK = 'http://example.com'
ORGANIZATION_TWITTER = 'https://twitter.com/example'
ORGANIZATION_FACEBOOK = 'https://www.facebook.com/example'
ORGANIZATION_ADDRESS_NAME = 'Main Office'
ORGANIZATION_ADDRESS_1 = '100 Main Street'
ORGANIZATION_ADDRESS_2 = 'Springfield, IL'
ORGANIZATION_ADDRESS_PHONE = '111.867.5309'
# String with the last date donation dropoffs will be accepted
DONATION_DROPOFF_FINAL_DATE = 'December 13th'

# List of places where donations can be dropped off.
# Appears in emails and in thank-you page.
# address_2, hours_2, and map_link are optional.
# Format:
# DONATION_DROPOFF_LOCATIONS = [{
#    'name': '',
#    'address_1': '',
#    'address_2': '',
#    'hours_1': '',
#    'hours_2': '',
#}]
DONATION_DROPOFF_LOCATIONS = [
  {
    'name': 'Test location',
    'address_1': '100 Main St',
    'address_2': 'Main Office',
    'hours_1': 'Monday-Friday: 10am-6pm',
    'hours_2': '',
    'map_link': 'http://maps.google.com?q=100 Main St, Springfield, IL'
  }
]
###

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# To send email via Gmail
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_HOST_USER = ORGANIZATION_EMAIL
# EMAIL_HOST_PASSWORD = 'PASSWORD_HERE'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'DEVELOPMENT_HOLIDAY_SEEKRIT_KEY'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATE_DEBUG = True

# use our own jQuery in static files for smart-selects
USE_DJANGO_JQUERY = False
JQUERY_URL = 'static/holiday/js/jquery-1.11.1.min.js'

# use our own bootstrap in static files for django-bootstrap
BOOTSTRAP3 = {
  'jquery_url': '/static/holiday/js/jquery-1.11.1.min.js',
  'base_url': '/static/holiday/',
  'css_url': None,
  'theme_url': None,
  'javascript_url': None,
  'horizontal_label_class': 'col-md-2',
  'horizontal_field_class': 'col-md-4',
}

# Always use IPython for shell_plus
SHELL_PLUS = "ipython"

TEMPLATE_CONTEXT_PROCESSORS = (
  "django.contrib.messages.context_processors.messages",
  "django.contrib.auth.context_processors.auth",
  "django.core.context_processors.debug",
  "django.core.context_processors.i18n",
  "django.core.context_processors.media",
  "django.core.context_processors.static",
  "django.core.context_processors.tz",
)

ALLOWED_HOSTS = ['*']

HTML_MINIFY = True

# Application definition
INSTALLED_APPS = (
  'holiday',
  'jstemplate',
  'django_admin_bootstrapped',
  'bootstrap3',
  'smart_selects',
  'django_extensions',
  'django.contrib.admin',
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.messages',
  'django.contrib.staticfiles',
  'django.contrib.admindocs',
  'formtools',
)

MIDDLEWARE_CLASSES = (
  'htmlmin.middleware.HtmlMinifyMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.middleware.common.CommonMiddleware',
  'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'holiday.urls'

WSGI_APPLICATION = 'holiday.wsgi.application'

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
  'default': {
      'ENGINE': 'django.db.backends.sqlite3',
      'NAME': os.path.join(BASE_DIR, 'holiday.db'),
  }
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'

print("static file dir: " + os.path.join(BASE_DIR, "static"))

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# URL of the login page.
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/check_first_login/'

# user
AUTH_PROFILE_MODULE = 'holiday.ProgramStaff'
