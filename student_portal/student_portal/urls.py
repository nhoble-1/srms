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
    Catches ALL errors including SystemExit (raised when Railway blocks
    the SMTP port at OS level) so the page never returns a 500.
    Real error is logged to Railway deploy logs for debugging.
    """
    template_name         = 'registration/password_reset_form.html'
    email_template_name   = 'registration/password_reset_email.txt'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url           = '/password-reset/sent/'

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except BaseException as exc:
            # Catches Exception AND SystemExit (port blocked at OS level)
            logger.error('Password reset email failed: %s', exc, exc_info=True)
            return redirect(self.success_url)


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
