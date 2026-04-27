import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


#  Security 
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-fallback-key-change-in-production',
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS', 'localhost 127.0.0.1'
).split()


#  Application definition 
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'anymail',
    'portal',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'student_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'student_portal.wsgi.application'


#  Database 
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


#  Password validation 
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


#  Internationalisation 
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Africa/Lagos'
USE_I18N      = True
USE_TZ        = True


#  Static files (WhiteNoise) 
STATIC_URL        = '/static/'
STATIC_ROOT       = BASE_DIR / 'staticfiles'
STATICFILES_DIRS  = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


#  Media / uploaded files 
# Cloudinary keeps uploaded files alive across Railway deploys.
# Add CLOUDINARY_URL to Railway → Variables to activate.
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '')

if CLOUDINARY_URL:
    INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL  = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
else:
    # No Cloudinary — local storage (profile pics won't persist on Railway redeploy)
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL  = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# Always ensure local media dirs exist (used as fallback)
import os as _os
for _d in ['media', 'media/profile_pics', 'media/receipts']:
    _os.makedirs(BASE_DIR / _d, exist_ok=True)


#  Authentication 
DEFAULT_AUTO_FIELD  = 'django.db.models.BigAutoField'
LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
MESSAGE_STORAGE     = 'django.contrib.messages.storage.session.SessionStorage'


#  Session security 
SESSION_COOKIE_AGE              = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


#  Email — Password Reset via Brevo HTTP API 
# Uses django-anymail which sends over HTTPS (port 443) — Railway
# never blocks this. No SMTP socket involved at all.
#
# In Railway → Variables add:
#   BREVO_API_KEY = your-brevo-api-key  (from Brevo → SMTP & API → API Keys)
#
# Your existing BREVO_SMTP_USER / BREVO_SMTP_PASSWORD are NOT used here —
# this uses the API Key instead which works over HTTPS.

BREVO_API_KEY      = os.environ.get('BREVO_API_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    'Admin <realshady02@gmail.com>',
)

if BREVO_API_KEY:
    # HTTP API — works on Railway, no SMTP ports needed
    EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
    ANYMAIL = {
        'BREVO_API_KEY': BREVO_API_KEY,
    }
else:
    # No API key — print reset link to Railway logs (for testing)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


#  Production security headers 
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER       = True
    SECURE_CONTENT_TYPE_NOSNIFF     = True
    SECURE_HSTS_SECONDS             = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS  = True
    SECURE_HSTS_PRELOAD             = True
    SECURE_SSL_REDIRECT             = False
    SECURE_PROXY_SSL_HEADER         = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE           = True
    CSRF_COOKIE_SECURE              = True
    X_FRAME_OPTIONS                 = 'DENY'
    CSRF_TRUSTED_ORIGINS            = [
        'https://student-portal-production-7f1d.up.railway.app',
        'https://*.up.railway.app',
    ]
