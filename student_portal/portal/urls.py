# portal/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('',                                    views.home,                 name='home'),
    path('register/',                           views.register_view,        name='register'),
    path('login/',                              views.login_view,           name='login'),
    path('logout/',                             views.logout_view,          name='logout'),
    path('dashboard/',                          views.dashboard,            name='dashboard'),
    path('profile/complete/',                   views.complete_profile,     name='complete_profile'),
    path('fee/<int:fee_id>/upload/',            views.upload_fee_receipt,   name='upload_fee_receipt'),
    path('semester/<str:level>/<str:semester>/',views.semester_detail,      name='semester_detail'),
    
    # PDF Generation
    path('result-slip/<str:level>/<str:semester>/', views.result_slip_pdf,  name='result_slip_pdf'),
    path('transcript/',                          views.transcript_pdf,       name='transcript_pdf'),
]