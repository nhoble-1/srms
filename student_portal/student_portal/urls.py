from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
import logging

logger = logging.getLogger(__name__)


class SafePasswordResetView(auth_views.PasswordResetView):
    """
    Overrides send_mail() directly so the try/except wraps the exact
    point where the SMTP call happens — before gunicorn can intercept it.
    """
    template_name         = 'registration/password_reset_form.html'
    email_template_name   = 'registration/password_reset_email.txt'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url           = '/password-reset/sent/'

    def form_valid(self, form):
        # Patch send_email on the form instance to catch all failures
        original_send = form.send_mail

        def safe_send(*args, **kwargs):
            try:
                return original_send(*args, **kwargs)
            except BaseException as exc:
                logger.error('Password reset email error: %s', exc, exc_info=True)

        form.send_mail = safe_send
        return super().form_valid(form)


urlpatterns = [
    path('admin/', admin.site.urls),

    path('password-reset/',
         SafePasswordResetView.as_view(),
         name='password_reset'),

    path('password-reset/sent/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html',
         ),
         name='password_reset_done'),

    path('password-reset/confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/password-reset/complete/',
         ),
         name='password_reset_confirm'),

    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html',
         ),
         name='password_reset_complete'),

    path('', include('portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=getattr(settings, 'MEDIA_ROOT', ''))
