# portal/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    Faculty, Department, Course, AcademicSession, Semester,
    StudentProfile, CourseRegistration, Result, Fee, FeePayment,
    GPAResult, CourseAllocation,
)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display   = ['name', 'code', 'dean', 'department_count', 'created_at']
    list_filter    = ['created_at']
    search_fields  = ['name', 'code']
    ordering       = ['name']

    def department_count(self, obj):
        return obj.departments.count()
    department_count.short_description = 'Departments'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'faculty', 'duration_years', 'course_count']
    list_filter   = ['faculty', 'duration_years']
    search_fields = ['name', 'code', 'faculty__name']
    ordering      = ['faculty__name', 'name']

    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = 'Courses'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display      = ['code', 'title', 'department', 'level', 'semester', 'credit_units', 'is_active']
    list_filter       = ['department', 'level', 'semester', 'is_active', 'is_elective']
    search_fields     = ['code', 'title']
    ordering          = ['department', 'level', 'semester', 'code']
    filter_horizontal = ['prerequisites']


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display   = ['name', 'start_year', 'end_year', 'is_current', 'start_date', 'end_date']
    list_editable  = ['is_current']
    list_filter    = ['is_current']
    search_fields  = ['name']
    ordering       = ['-start_year']
    actions        = ['set_as_current']

    def set_as_current(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, 'Please select only one session.', level='error')
            return
        session = queryset.first()
        AcademicSession.objects.filter(is_current=True).update(is_current=False)
        session.is_current = True
        session.save()
        self.message_user(request, f'{session.name} set as current session.')
    set_as_current.short_description = 'Set as current session'


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'session', 'semester', 'is_current', 'start_date', 'end_date']
    list_filter   = ['session', 'semester', 'is_current']
    search_fields = ['session__name']
    ordering      = ['-session__name', 'semester']
    actions       = ['set_as_current']

    def set_as_current(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, 'Please select only one semester.', level='error')
            return
        semester = queryset.first()
        Semester.objects.filter(is_current=True).update(is_current=False)
        semester.is_current = True
        semester.save()
        self.message_user(request, f'{semester} set as current semester.')
    set_as_current.short_description = 'Set as current semester'


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display  = [
        'matric_number', 'get_full_name', 'department', 'current_level',
        'current_semester', 'cgpa', 'profile_completed', 'created_at',
    ]
    list_filter   = [
        'department', 'current_level', 'current_semester',
        'profile_completed', 'academic_standing', 'mode_of_entry',
    ]
    search_fields  = ['matric_number', 'user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'cgpa', 'total_grade_points', 'total_credit_units_earned']
    ordering       = ['matric_number']
    actions        = ['recalculate_cgpa']

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'

    def recalculate_cgpa(self, request, queryset):
        for profile in queryset:
            profile.calculate_cgpa()
        self.message_user(request, f'CGPA recalculated for {queryset.count()} student(s).')
    recalculate_cgpa.short_description = 'Recalculate CGPA for selected students'


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display  = ['student', 'course', 'session', 'semester', 'is_approved', 'registration_date']
    list_filter   = ['session', 'semester', 'is_approved', 'is_carryover', 'course__department']
    search_fields = ['student__matric_number', 'course__code']
    ordering      = ['-session__name', 'course__code']
    actions       = ['approve_registrations']

    def approve_registrations(self, request, queryset):
        queryset.update(is_approved=True, approved_by=request.user)
        self.message_user(request, f'{queryset.count()} registration(s) approved.')
    approve_registrations.short_description = 'Approve selected registrations'


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display  = ['student', 'course', 'session', 'total_score', 'get_grade_colored', 'status', 'uploaded_at']
    list_filter   = ['session', 'status', 'grade', 'course__department', 'course__level', 'course__semester']
    search_fields = [
        'student__matric_number', 'student__user__first_name',
        'student__user__last_name', 'course__code', 'course__title',
    ]
    ordering         = ['-uploaded_at']
    # autocomplete_fields removed — use raw_id_fields for better compatibility
    raw_id_fields    = ['student', 'course']
    readonly_fields  = ['total_score', 'grade', 'grade_point', 'score']
    actions          = ['approve_results', 'publish_results']

    def get_grade_colored(self, obj):
        total = float(obj.total_score)
        if total >= 70:
            color = '#28a745'
        elif total >= 60:
            color = '#17a2b8'
        elif total >= 50:
            color = '#ffc107'
        elif total >= 45:
            color = '#fd7e14'
        else:
            color = '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ({})</span>',
            color, obj.get_grade_label(), obj.grade,
        )
    get_grade_colored.short_description = 'Grade'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    def approve_results(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f'{queryset.count()} result(s) approved.')
    approve_results.short_description = 'Approve selected results'

    def publish_results(self, request, queryset):
        queryset.update(
            status='published',
            published_by=request.user,
            publication_date=timezone.now(),
        )
        self.message_user(request, f'{queryset.count()} result(s) published.')
    publish_results.short_description = 'Publish selected results'


@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ['department', 'level', 'semester', 'session', 'get_total']
    list_filter  = ['department', 'level', 'semester', 'session']
    ordering     = ['department', 'level', 'semester']

    def get_total(self, obj):
        return f'₦{obj.total_amount():,.2f}'
    get_total.short_description = 'Total Amount'


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display  = [
        'student', 'fee', 'amount_paid', 'payment_date',
        'status', 'transaction_reference', 'submitted_at',
    ]
    list_filter   = ['status', 'fee__department', 'fee__session']
    search_fields = [
        'student__matric_number', 'transaction_reference',
        'student__user__first_name', 'student__user__last_name',
    ]
    ordering = ['-submitted_at']
    actions  = ['verify_payments', 'reject_payments']

    def verify_payments(self, request, queryset):
        updated = queryset.update(
            status='paid',
            verified_by=request.user,
            verified_at=timezone.now(),
        )
        self.message_user(request, f'{updated} payment(s) verified successfully.')
    verify_payments.short_description = '✓ Verify selected payments'

    def reject_payments(self, request, queryset):
        updated = queryset.update(status='unpaid')
        self.message_user(request, f'{updated} payment(s) marked as unpaid.')
    reject_payments.short_description = '✗ Reject selected payments'


@admin.register(GPAResult)
class GPAResultAdmin(admin.ModelAdmin):
    list_display  = ['student', 'session', 'semester', 'gpa', 'total_credits', 'calculated_at']
    list_filter   = ['session', 'semester']
    search_fields = ['student__matric_number', 'student__user__first_name']
    ordering      = ['-session__name', '-semester__semester']


@admin.register(CourseAllocation)
class CourseAllocationAdmin(admin.ModelAdmin):
    list_display  = ['lecturer', 'course', 'session', 'is_coordinator', 'assigned_at']
    list_filter   = ['session', 'is_coordinator', 'course__department']
    search_fields = ['lecturer__first_name', 'lecturer__last_name', 'course__code']
    ordering      = ['-session__name', 'course__code']


# Customise admin site header
admin.site.site_header  = 'UNIQUE OPEN UNIVERSITY'
admin.site.site_title   = 'Admin Panel'
admin.site.index_title  = 'Admistration Dashboard'
