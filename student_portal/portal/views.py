# portal/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.cache import never_cache
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, Image,
)

from .models import (
    StudentProfile, Department, Course, AcademicSession, Semester,
    Result, Fee, FeePayment, GPAResult, CourseRegistration,
    SEMESTER_CHOICES,
)
from .forms import StudentRegistrationForm, StudentProfileForm, FeePaymentForm


#  Brand colours 
NAVY  = colors.HexColor('#1a3a5c')
GOLD  = colors.HexColor('#c8952a')
LGREY = colors.HexColor('#f4f6fb')
DGREY = colors.HexColor('#4a5568')
WHITE = colors.white
BLACK = colors.black


# PDF helpers
def _pdf_styles():
    return {
        'uni':      ParagraphStyle('uni',      fontSize=15, fontName='Helvetica-Bold',
                                   textColor=NAVY,  spaceAfter=2, alignment=TA_CENTER),
        'sub':      ParagraphStyle('sub',      fontSize=8,  fontName='Helvetica',
                                   textColor=DGREY, spaceAfter=2, alignment=TA_CENTER),
        'title':    ParagraphStyle('title',    fontSize=12, fontName='Helvetica-Bold',
                                   textColor=NAVY,  spaceAfter=4, alignment=TA_CENTER),
        'label':    ParagraphStyle('label',    fontSize=8,  fontName='Helvetica-Bold',
                                   textColor=DGREY),
        'value':    ParagraphStyle('value',    fontSize=9,  fontName='Helvetica',
                                   textColor=BLACK),
        'section':  ParagraphStyle('section',  fontSize=9,  fontName='Helvetica-Bold',
                                   textColor=WHITE),
        'footer':   ParagraphStyle('footer',   fontSize=7,  fontName='Helvetica',
                                   textColor=DGREY, alignment=TA_CENTER),
        'cell_c':   ParagraphStyle('cell_c',   fontSize=8,  fontName='Helvetica',
                                   textColor=BLACK, alignment=TA_CENTER),
        'cell_l':   ParagraphStyle('cell_l',   fontSize=8,  fontName='Helvetica',
                                   textColor=BLACK, alignment=TA_LEFT),
    }


def _result_table_style():
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  NAVY),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  7),
        ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, 0),  6),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  6),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.0, NAVY),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ALIGN',         (2, 1), (-1, -1), 'CENTER'),
        ('ALIGN',         (0, 1), (1, -1),  'LEFT'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, LGREY]),
        ('TOPPADDING',    (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
    ])


def _section_heading(label, s):
    tbl = Table([[Paragraph(label, s['section'])]], colWidths=['100%'])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), NAVY),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
    ]))
    return tbl


def _info_table_style():
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LGREY),
        ('BOX',           (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ])


def _get_photo_element(profile, width, height):
    """Return an Image element if profile picture exists, else a placeholder."""
    if profile.profile_picture and profile.profile_picture.name:
        try:
            # .path works for local storage; for Cloudinary use the URL via urllib
            try:
                img_path = profile.profile_picture.path
            except NotImplementedError:
                # Cloudinary storage doesn't support .path — fetch via URL
                import urllib.request, tempfile, os
                url = profile.profile_picture.url
                suffix = os.path.splitext(url.split('?')[0])[-1] or '.jpg'
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                urllib.request.urlretrieve(url, tmp.name)
                img_path = tmp.name
            img = Image(img_path, width=width, height=height)
            img.hAlign = 'CENTER'
            return img
        except Exception:
            pass
    return Paragraph('<i>No Photo</i>', ParagraphStyle(
        'np', fontSize=7, fontName='Helvetica', textColor=DGREY, alignment=TA_CENTER,
    ))


def _build_result_slip_pdf(profile, level, semester_label, course_data,
                            total_credits, gpa, cgpa, generated_date):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s     = _pdf_styles()
    story = []

    # Header
    story.append(Paragraph('UNIQUE OPEN UNIVERSITY', s['uni']))
    story.append(Spacer(1, 5))
    story.append(Paragraph('Student Result Management System', s['sub']))
    story.append(Spacer(1, 5))
    story.append(Paragraph('SEMESTER RESULT SLIP', s['title']))
    story.append(Spacer(1, 5))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY, spaceAfter=8))

    # Student info + passport photo side by side
    PHOTO_W, PHOTO_H = 2.8*cm, 3.5*cm
    info_rows = [
        [Paragraph('<b>Name:</b>',          s['label']),
         Paragraph(profile.get_full_name(), s['value']),
         Paragraph('<b>Matric No:</b>',     s['label']),
         Paragraph(profile.matric_number,   s['value'])],
        [Paragraph('<b>Department:</b>',    s['label']),
         Paragraph(profile.department.name, s['value']),
         Paragraph('<b>Level:</b>',         s['label']),
         Paragraph(f'{level} Level',        s['value'])],
        [Paragraph('<b>Semester:</b>',      s['label']),
         Paragraph(semester_label,          s['value']),
         Paragraph('<b>Session:</b>',       s['label']),
         Paragraph(str(profile.current_session) if profile.current_session else '—',
                   s['value'])],
    ]
    # inner cols sum to 13.8cm, outer = 13.8 + 3.2 = 17.0cm usable width
    info_tbl = Table(info_rows, colWidths=[2.3*cm, 4.8*cm, 2.3*cm, 4.4*cm])
    info_tbl.setStyle(_info_table_style())

    photo = _get_photo_element(profile, PHOTO_W, PHOTO_H)

    outer = Table([[info_tbl, photo]], colWidths=[13.8*cm, PHOTO_W + 0.4*cm])
    outer.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (1, 0), (1, 0),   'CENTER'),
        ('BOX',           (1, 0), (1, 0),   1.0, NAVY),
        ('BACKGROUND',    (1, 0), (1, 0),   LGREY),
        ('TOPPADDING',    (1, 0), (1, 0),   3),
        ('BOTTOMPADDING', (1, 0), (1, 0),   3),
        ('LEFTPADDING',   (1, 0), (1, 0),   3),
        ('RIGHTPADDING',  (1, 0), (1, 0),   3),
    ]))
    story.append(outer)
    story.append(Spacer(1, 10))

    # Course results table
    story.append(_section_heading('COURSE RESULTS', s))
    headers = [['#', 'Code', 'Course Title', 'Cr', 'CA', 'Exam', 'Total', 'Grd', 'GP']]
    rows = []
    for i, item in enumerate(course_data, 1):
        r = item['result']
        rows.append([
            str(i),
            item['course'].code,
            item['course'].title,
            str(item['course'].credit_units),
            str(r.ca_score)    if r else '—',
            str(r.exam_score)  if r else '—',
            str(r.total_score) if r else '—',
            r.grade            if r else '—',
            str(r.grade_point) if r else '—',
        ])
    col_w = [0.6*cm, 2.3*cm, 6.8*cm, 1.0*cm, 1.1*cm, 1.2*cm, 1.2*cm, 1.0*cm, 1.0*cm]
    tbl = Table(headers + rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(_result_table_style())
    story.append(tbl)
    story.append(Spacer(1, 10))

    # Summary
    summary_data = [
        ['Total Credit Units', 'Semester GPA', 'Cumulative CGPA'],
        [str(total_credits),   str(gpa),        str(cgpa)],
    ]
    sum_tbl = Table(summary_data, colWidths=[5.67*cm, 5.67*cm, 5.66*cm])
    sum_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LGREY),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica'),
        ('FONTSIZE',      (0, 0), (-1, 0),  7),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  DGREY),
        ('FONTNAME',      (0, 1), (-1, 1),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 1), (-1, 1),  10),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('BOX',           (0, 0), (-1, -1), 1.0, NAVY),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 20))

    # Footer
    story.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#cbd5e1')))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Generated: {generated_date.strftime("%B %d, %Y  %H:%M")}  |  '
        'Electronically generated — no signature required.',
        s['footer'],
    ))

    doc.build(story)
    return buf.getvalue()


def _build_transcript_pdf(profile, transcript_data, cgpa,
                           classification, generated_date):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s     = _pdf_styles()
    story = []

    story.append(Paragraph('UNIQUE OPEN UNIVERSITY', s['uni']))
    story.append(Spacer(1, 5))
    story.append(Paragraph('OFFICIAL ACADEMIC TRANSCRIPT', s['title']))
    story.append(Spacer(1, 5))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY, spaceAfter=8))

    # Student info + passport photo side by side
    # A4 usable width = 17.0cm (21cm - 2cm margins each side)
    # Photo col = 2.8 + 0.4 padding = 3.2cm → info col = 13.8cm
    PHOTO_W, PHOTO_H = 2.8*cm, 3.5*cm
    info_rows = [
        [Paragraph('<b>Name:</b>',            s['label']),
         Paragraph(profile.get_full_name(),   s['value']),
         Paragraph('<b>Matric No:</b>',        s['label']),
         Paragraph(profile.matric_number,      s['value'])],
        [Paragraph('<b>Department:</b>',       s['label']),
         Paragraph(profile.department.name,    s['value']),
         Paragraph('<b>Faculty:</b>',          s['label']),
         Paragraph(profile.department.faculty.name, s['value'])],
        [Paragraph('<b>Mode of Entry:</b>',    s['label']),
         Paragraph(profile.mode_of_entry,      s['value']),
         Paragraph('<b>Entry Year:</b>',        s['label']),
         Paragraph(profile.entry_year or '—',  s['value'])],
    ]
    # inner cols sum to 13.8cm exactly
    info_tbl = Table(info_rows, colWidths=[2.3*cm, 4.8*cm, 2.3*cm, 4.4*cm])
    info_tbl.setStyle(_info_table_style())

    photo = _get_photo_element(profile, PHOTO_W, PHOTO_H)

    # outer cols: 13.8 + 3.2 = 17.0cm = exact usable width
    outer = Table([[info_tbl, photo]], colWidths=[13.8*cm, PHOTO_W + 0.4*cm])
    outer.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (1, 0), (1, 0),   'CENTER'),
        ('BOX',           (1, 0), (1, 0),   1.0, NAVY),
        ('BACKGROUND',    (1, 0), (1, 0),   LGREY),
        ('TOPPADDING',    (1, 0), (1, 0),   3),
        ('BOTTOMPADDING', (1, 0), (1, 0),   3),
        ('LEFTPADDING',   (1, 0), (1, 0),   3),
        ('RIGHTPADDING',  (1, 0), (1, 0),   3),
    ]))
    story.append(outer)
    story.append(Spacer(1, 12))

    headers = [['Code', 'Course Title', 'Cr', 'Score', 'Grd', 'GP']]
    col_w   = [2.5*cm, 9.0*cm, 1.2*cm, 1.5*cm, 1.2*cm, 1.6*cm]

    for section_key, results in transcript_data.items():
        story.append(_section_heading(section_key, s))
        rows = [
            [r.course.code, r.course.title,
             str(r.course.credit_units),
             str(r.total_score), r.grade, str(r.grade_point)]
            for r in results
        ]
        tbl = Table(headers + rows, colWidths=col_w, repeatRows=1)
        tbl.setStyle(_result_table_style())
        story.append(tbl)
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 6))
    summary_data = [
        ['Cumulative GPA (CGPA)', 'Degree Classification'],
        [str(cgpa), classification],
    ]
    sum_tbl = Table(summary_data, colWidths=[8.5*cm, 8.5*cm])
    sum_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LGREY),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica'),
        ('FONTSIZE',      (0, 0), (-1, 0),  7),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  DGREY),
        ('FONTNAME',      (0, 1), (-1, 1),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 1), (-1, 1),  10),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX',           (0, 0), (-1, -1), 1.0, NAVY),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#cbd5e1')))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Generated: {generated_date.strftime("%B %d, %Y")}  |  Official transcript.',
        s['footer'],
    ))

    doc.build(story)
    return buf.getvalue()


# Helpers
def _get_profile_or_none(request):
    try:
        return request.user.student_profile
    except StudentProfile.DoesNotExist:
        return None


# Public views
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@never_cache
@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user            = form.save(commit=False)
                    user.first_name = form.cleaned_data['first_name']
                    user.last_name  = form.cleaned_data['last_name']
                    user.email      = form.cleaned_data['email']
                    user.save()

                    current_session  = AcademicSession.objects.filter(is_current=True).first()
                    current_semester = Semester.objects.filter(is_current=True).first()
                    matric           = form.cleaned_data['matric_number']

                    StudentProfile.objects.create(
                        user=user,
                        matric_number=matric,
                        department=form.cleaned_data['department'],
                        current_session=current_session,
                        current_semester=current_semester.semester if current_semester else 'First',
                        entry_year=matric[:2] if len(matric) >= 2 else '',
                    )
                messages.success(request, 'Registration successful! Please log in.')
                return redirect('login')
            except Exception:
                messages.error(request, 'Registration failed. Please try again.')
    else:
        form = StudentRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


@never_cache
@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get('next', '')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been signed out successfully.')
    return redirect('login')


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def complete_profile(request):
    profile = _get_profile_or_none(request)
    if not profile:
        messages.error(request, 'Student profile not found. Please contact admin.')
        return redirect('login')

    if profile.profile_completed:
        messages.warning(request,
            'Your profile has already been saved and cannot be edited. '
            'Contact the admin for any corrections.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentProfileForm(
            request.POST, request.FILES,
            instance=profile, user=request.user,
        )
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Profile saved successfully! Welcome.')
                return redirect('dashboard')
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error('Profile save error: %s', exc, exc_info=True)
                messages.error(request,
                    'There was a problem saving your profile picture. '
                    'Please try a smaller image (under 1MB) or a JPG/PNG file.')
    else:
        form = StudentProfileForm(instance=profile, user=request.user)

    return render(request, 'portal/complete_profile.html', {
        'form': form, 'profile': profile,
    })


@never_cache
@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect('/admin/')

    profile = _get_profile_or_none(request)
    if not profile:
        messages.error(request, 'Student profile not found. Please contact admin.')
        return redirect('login')

    if not profile.profile_completed:
        return redirect('complete_profile')

    current_session  = AcademicSession.objects.filter(is_current=True).first()
    current_semester = Semester.objects.filter(is_current=True).first()

    current_courses = Course.objects.filter(
        department=profile.department,
        level=profile.current_level,
        semester=profile.current_semester,
        is_active=True,
    ).order_by('code')

    current_results      = Result.objects.filter(
        student=profile,
        course__level=profile.current_level,
        course__semester=profile.current_semester,
    ).select_related('course')
    current_results_dict = {r.course_id: r for r in current_results}
    current_course_data  = [
        {'course': c, 'result': current_results_dict.get(c.id)}
        for c in current_courses
    ]

    current_gpa = None
    if current_session and current_semester:
        gpa_obj = GPAResult.objects.filter(
            student=profile, session=current_session, semester=current_semester,
        ).first()
        if gpa_obj:
            current_gpa = gpa_obj.gpa

    past_semesters  = []
    reached_current = False

    for level in profile.department.get_levels():
        if reached_current:
            break
        for sem in ['First', 'Second']:
            if level == profile.current_level and sem == profile.current_semester:
                reached_current = True
                break

            courses = Course.objects.filter(
                department=profile.department,
                level=level, semester=sem, is_active=True,
            ).order_by('code')

            results = Result.objects.filter(
                student=profile,
                course__level=level, course__semester=sem,
            ).select_related('course')

            fee = Fee.objects.filter(
                department=profile.department, level=level, semester=sem,
            ).first()

            fee_payment = (
                FeePayment.objects.filter(student=profile, fee=fee).first()
                if fee else None
            )

            result_dict = {r.course_id: r for r in results}
            course_data = [
                {'course': c, 'result': result_dict.get(c.id)} for c in courses
            ]

            avg = None
            if results.exists():
                avg = round(sum(float(r.total_score) for r in results) / results.count(), 2)

            past_semesters.append({
                'level':            level,
                'semester':         sem,
                'semester_display': dict(SEMESTER_CHOICES).get(sem, sem),
                'courses':          course_data,
                'average':          avg,
                'fee':              fee,
                'fee_payment':      fee_payment,
                'has_results':      results.exists(),
            })

    current_fee = Fee.objects.filter(
        department=profile.department,
        level=profile.current_level,
        semester=profile.current_semester,
    ).first()

    current_fee_payment = (
        FeePayment.objects.filter(student=profile, fee=current_fee).first()
        if current_fee else None
    )

    profile.calculate_cgpa()

    return render(request, 'portal/dashboard.html', {
        'profile':             profile,
        'past_semesters':      past_semesters,
        'current_courses':     current_course_data,
        'current_fee':         current_fee,
        'current_fee_payment': current_fee_payment,
        'current_gpa':         current_gpa,
        'classification':      profile.get_classification(),
    })


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def upload_fee_receipt(request, fee_id):
    profile = _get_profile_or_none(request)
    if not profile:
        messages.error(request, 'Student profile not found.')
        return redirect('login')

    fee              = get_object_or_404(Fee, id=fee_id, department=profile.department)
    existing_payment = FeePayment.objects.filter(student=profile, fee=fee).first()

    if existing_payment and existing_payment.status == 'paid':
        messages.info(request, 'This fee has already been verified as paid.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = FeePaymentForm(request.POST, request.FILES, fee=fee, student=profile)
        if form.is_valid():
            if existing_payment:
                existing_payment.delete()
            payment         = form.save(commit=False)
            payment.student = profile
            payment.fee     = fee
            payment.status  = 'pending'
            payment.save()
            messages.success(request,
                'Receipt submitted! It will be verified by the admin.')
            return redirect('dashboard')
    else:
        form = FeePaymentForm(fee=fee, student=profile)

    return render(request, 'portal/upload_receipt.html', {
        'form': form, 'fee': fee, 'profile': profile,
        'existing_payment': existing_payment,
    })


@login_required
def semester_detail(request, level, semester):
    profile = _get_profile_or_none(request)
    if not profile:
        return redirect('login')

    if level not in ['100', '200', '300', '400', '500'] or \
       semester not in ['First', 'Second']:
        messages.error(request, 'Invalid semester reference.')
        return redirect('dashboard')

    courses = Course.objects.filter(
        department=profile.department,
        level=level, semester=semester, is_active=True,
    ).order_by('code')

    results = Result.objects.filter(
        student=profile, course__level=level, course__semester=semester,
    ).select_related('course', 'session')

    result_dict = {r.course_id: r for r in results}
    course_data = [{'course': c, 'result': result_dict.get(c.id)} for c in courses]

    avg = None
    if results.exists():
        avg = round(sum(float(r.total_score) for r in results) / results.count(), 2)

    fee = Fee.objects.filter(
        department=profile.department, level=level, semester=semester,
    ).first()
    fee_payment = (
        FeePayment.objects.filter(student=profile, fee=fee).first() if fee else None
    )

    return render(request, 'portal/semester_detail.html', {
        'profile': profile, 'level': level, 'semester': semester,
        'semester_display': {'First': 'First Semester', 'Second': 'Second Semester'}.get(semester),
        'courses': course_data, 'average': avg,
        'fee': fee, 'fee_payment': fee_payment,
    })


# PDF views — ReportLab (pure Python, works on Railway)
@login_required
def result_slip_pdf(request, level, semester):
    profile = _get_profile_or_none(request)
    if not profile:
        return redirect('login')

    if level not in ['100', '200', '300', '400', '500'] or \
       semester not in ['First', 'Second']:
        messages.error(request, 'Invalid semester reference.')
        return redirect('dashboard')

    courses = Course.objects.filter(
        department=profile.department,
        level=level, semester=semester, is_active=True,
    ).order_by('code')

    results = Result.objects.filter(
        student=profile, course__level=level,
        course__semester=semester, status='published',
    ).select_related('course')

    result_dict        = {r.course_id: r for r in results}
    course_data        = [{'course': c, 'result': result_dict.get(c.id)} for c in courses]
    total_credits      = sum(item['course'].credit_units for item in course_data)
    total_grade_points = Decimal('0.00')

    for item in course_data:
        if item['result']:
            total_grade_points += (
                item['result'].grade_point * item['result'].course.credit_units
            )

    gpa = (
        (total_grade_points / Decimal(str(total_credits))).quantize(Decimal('0.01'))
        if total_credits > 0 else Decimal('0.00')
    )

    try:
        pdf_bytes = _build_result_slip_pdf(
            profile        = profile,
            level          = level,
            semester_label = {'First': 'First Semester', 'Second': 'Second Semester'}.get(semester, semester),
            course_data    = course_data,
            total_credits  = total_credits,
            gpa            = gpa,
            cgpa           = profile.cgpa,
            generated_date = timezone.now(),
        )
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = (
            f'inline; filename="result_slip_{profile.matric_number}_{level}L_{semester}.pdf"'
        )
        return resp
    except Exception as e:
        messages.error(request, 'Error generating PDF. Please try again.')
        return redirect('dashboard')


@login_required
def transcript_pdf(request):
    profile = _get_profile_or_none(request)
    if not profile:
        return redirect('login')

    results = Result.objects.filter(
        student=profile, status='published',
    ).select_related('course', 'session', 'semester').order_by(
        'session__name', 'semester__semester', 'course__level',
    )

    transcript_data = {}
    for result in results:
        key = (
            f"{result.session.name} — "
            f"{result.course.get_semester_display()} ({result.course.level}L)"
        )
        transcript_data.setdefault(key, []).append(result)

    try:
        pdf_bytes = _build_transcript_pdf(
            profile         = profile,
            transcript_data = transcript_data,
            cgpa            = profile.cgpa,
            classification  = profile.get_classification(),
            generated_date  = timezone.now(),
        )
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = (
            f'inline; filename="transcript_{profile.matric_number}.pdf"'
        )
        return resp
    except Exception:
        messages.error(request, 'Error generating PDF. Please try again.')
        return redirect('dashboard')
