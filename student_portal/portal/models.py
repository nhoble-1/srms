# portal/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from decimal import Decimal, ROUND_HALF_UP


LEVEL_CHOICES = [
    ('100', '100 Level'),
    ('200', '200 Level'),
    ('300', '300 Level'),
    ('400', '400 Level'),
    ('500', '500 Level'),
]

SEMESTER_CHOICES = [
    ('First',  'First Semester'),
    ('Second', 'Second Semester'),
]

FEE_STATUS_CHOICES = [
    ('unpaid',  'Unpaid'),
    ('pending', 'Pending Verification'),
    ('paid',    'Paid'),
]

RESULT_STATUS_CHOICES = [
    ('pending',   'Pending'),
    ('approved',  'Approved by Lecturer'),
    ('verified',  'Verified by HOD'),
    ('published', 'Published'),
]


class Faculty(models.Model):
    """Faculty model (e.g., Faculty of Science, Faculty of Arts)"""

    name        = models.CharField(max_length=200, unique=True)
    code        = models.CharField(max_length=10, unique=True)
    dean        = models.CharField(max_length=200, blank=True, help_text='Name of the Dean')
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name_plural = 'Faculties'
        ordering = ['name']


class Department(models.Model):
    """Department model linked to Faculty"""

    name           = models.CharField(max_length=200)
    code           = models.CharField(max_length=10, unique=True)
    faculty        = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')
    description    = models.TextField(blank=True)
    duration_years = models.IntegerField(default=4, choices=[(4, '4 Years'), (5, '5 Years')])
    hod            = models.CharField(max_length=200, blank=True, help_text='Name of the HOD')
    current_levels = models.IntegerField(
        default=4,
        help_text='Number of levels in department (e.g., 4 for 100-400 level)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering      = ['faculty__name', 'name']
        unique_together = ['name', 'faculty']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_levels(self):
        """Return list of level strings based on duration."""
        levels = ['100', '200', '300', '400']
        if self.duration_years == 5:
            levels.append('500')
        return levels


class AcademicSession(models.Model):
    """Academic session (e.g., 2024/2025)"""

    name = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(
            r'^\d{4}/\d{4}$',
            message='Session must be in format: 2024/2025',
        )],
    )
    start_year = models.IntegerField()
    end_year   = models.IntegerField()
    is_current = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date   = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicSession.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-start_year']


class Semester(models.Model):
    """Semester within an academic session"""

    session             = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='semesters')
    semester            = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    is_current          = models.BooleanField(default=False)
    start_date          = models.DateField()
    end_date            = models.DateField()
    registration_start  = models.DateField()
    registration_end    = models.DateField()
    result_entry_start  = models.DateField(null=True, blank=True)
    result_entry_end    = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.session.name} - {self.semester}"

    def save(self, *args, **kwargs):
        if self.is_current:
            Semester.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    class Meta:
        ordering        = ['-session__name', 'semester']
        unique_together = ['session', 'semester']


class Course(models.Model):
    """Course model with credit hours and level"""

    department        = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    code              = models.CharField(max_length=20)
    title             = models.CharField(max_length=200)
    credit_units      = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(6)])
    level             = models.CharField(max_length=3, choices=LEVEL_CHOICES)
    semester          = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    description       = models.TextField(blank=True)
    is_elective       = models.BooleanField(default=False)
    is_general_studies = models.BooleanField(default=False)
    prerequisites     = models.ManyToManyField('self', symmetrical=False, blank=True)
    is_active         = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering        = ['level', 'semester', 'code']
        unique_together = ['department', 'code', 'level', 'semester']

    def __str__(self):
        return f"{self.code} - {self.title} ({self.department.code} {self.level}L)"


class StudentProfile(models.Model):
    """Extended profile for student users"""

    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    matric_number    = models.CharField(max_length=20, unique=True)
    department       = models.ForeignKey(Department, on_delete=models.PROTECT)
    current_level    = models.CharField(max_length=3, choices=LEVEL_CHOICES, default='100')
    current_semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default='First')
    current_session  = models.ForeignKey(
        AcademicSession, on_delete=models.SET_NULL, null=True, blank=True,
    )
    entry_year    = models.CharField(max_length=4, blank=True, help_text='Year of entry (e.g., 2022)')
    mode_of_entry = models.CharField(
        max_length=20,
        choices=[('UTME', 'UTME'), ('DE', 'Direct Entry')],
        default='UTME',
    )
    phone              = models.CharField(max_length=15, blank=True)
    address            = models.TextField(blank=True)
    date_of_birth      = models.DateField(null=True, blank=True)
    profile_picture    = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    profile_completed  = models.BooleanField(default=False)

    # CGPA fields
    cgpa                      = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    total_credit_units_earned = models.IntegerField(default=0)
    total_grade_points        = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    academic_standing         = models.CharField(
        max_length=20,
        choices=[('Good', 'Good Standing'), ('Probation', 'Probation'), ('Withdrawn', 'Withdrawn')],
        default='Good',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.matric_number} - {self.user.get_full_name()}"

    def get_full_name(self):
        return self.user.get_full_name() or self.user.username

    def get_current_semester_display(self):
        return dict(SEMESTER_CHOICES).get(self.current_semester, self.current_semester)

    def get_semester_sessions(self):
        """Returns all level+semester combos up to current level/semester."""
        levels   = self.department.get_levels()
        sessions = []
        for level in levels:
            for sem in ['First', 'Second']:
                sessions.append({'level': level, 'semester': sem})
                if level == self.current_level and sem == self.current_semester:
                    return sessions
        return sessions

    def get_past_semesters(self):
        all_sessions = self.get_semester_sessions()
        current      = {'level': self.current_level, 'semester': self.current_semester}
        return [s for s in all_sessions if s != current]

    def calculate_cgpa(self):
        """Calculate CGPA from all approved/verified/published results."""
        results = Result.objects.filter(
            student=self,
            status__in=['approved', 'verified', 'published'],
        ).select_related('course')

        total_grade_points = Decimal('0.00')
        total_credits      = 0

        for result in results:
            total_grade_points += Decimal(str(result.grade_point)) * result.course.credit_units
            total_credits      += result.course.credit_units

        if total_credits > 0:
            cgpa = total_grade_points / Decimal(str(total_credits))
            self.cgpa = cgpa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            self.cgpa = Decimal('0.00')

        self.total_grade_points        = total_grade_points
        self.total_credit_units_earned = total_credits
        self.save(update_fields=['cgpa', 'total_grade_points', 'total_credit_units_earned', 'updated_at'])
        return self.cgpa

    def get_classification(self):
        """Get degree classification based on CGPA."""
        if self.cgpa >= Decimal('4.50'):
            return 'First Class Honours'
        elif self.cgpa >= Decimal('3.50'):
            return 'Second Class Honours (Upper Division)'
        elif self.cgpa >= Decimal('2.40'):
            return 'Second Class Honours (Lower Division)'
        elif self.cgpa >= Decimal('1.50'):
            return 'Third Class Honours'
        elif self.cgpa >= Decimal('1.00'):
            return 'Pass'
        return 'Fail'

    def get_semester_average(self, level, semester):
        results = self.results.filter(course__level=level, course__semester=semester)
        if results.exists():
            total = sum(float(r.total_score) for r in results)
            return round(total / results.count(), 2)
        return None


class CourseRegistration(models.Model):
    """Student course registration per session/semester"""

    student           = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='registrations')
    course            = models.ForeignKey(Course, on_delete=models.CASCADE)
    session           = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    semester          = models.ForeignKey(Semester, on_delete=models.CASCADE)
    registration_date = models.DateTimeField(auto_now_add=True)
    is_approved       = models.BooleanField(default=False)
    approved_by       = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_registrations',
    )
    is_carryover = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.matric_number} - {self.course.code}"

    class Meta:
        unique_together = ['student', 'course', 'session', 'semester']
        ordering        = ['-session__name', 'course__code']


class Result(models.Model):
    """Student result for each registered course"""

    GRADE_CHOICES = (
        ('A', 'A (70-100)'),
        ('B', 'B (60-69)'),
        ('C', 'C (50-59)'),
        ('D', 'D (45-49)'),
        ('E', 'E (40-44)'),
        ('F', 'F (0-39)'),
    )

    student  = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='results')
    course   = models.ForeignKey(Course, on_delete=models.CASCADE)
    session  = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, null=True, blank=True)

    ca_score   = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(30)],
    )
    exam_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(70)],
    )
    total_score = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    # Legacy field kept in sync with total_score
    score = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Legacy score field (mirrors total_score)',
    )

    grade       = models.CharField(max_length=1, choices=GRADE_CHOICES, editable=False)
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, editable=False, default=Decimal('0.0'))

    status = models.CharField(max_length=20, choices=RESULT_STATUS_CHOICES, default='pending')

    uploaded_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='uploaded_results',
    )
    uploaded_at  = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    verified_by      = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_results',
    )
    verification_date = models.DateTimeField(null=True, blank=True)

    published_by     = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='published_results',
    )
    publication_date = models.DateTimeField(null=True, blank=True)

    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ['student', 'course', 'session']
        ordering        = ['course__level', 'course__semester', 'course__code']

    def __str__(self):
        return f"{self.student.matric_number} - {self.course.code}: {self.total_score}"

    def calculate_grade(self):
        """Calculate letter grade and grade point based on total score."""
        total = float(self.total_score)
        if total >= 70:
            self.grade, self.grade_point = 'A', Decimal('5.0')
        elif total >= 60:
            self.grade, self.grade_point = 'B', Decimal('4.0')
        elif total >= 50:
            self.grade, self.grade_point = 'C', Decimal('3.0')
        elif total >= 45:
            self.grade, self.grade_point = 'D', Decimal('2.0')
        elif total >= 40:
            self.grade, self.grade_point = 'E', Decimal('1.0')
        else:
            self.grade, self.grade_point = 'F', Decimal('0.0')
        return self.grade, self.grade_point

    def save(self, *args, **kwargs):
        self.total_score = self.ca_score + self.exam_score
        self.score       = self.total_score   # keep legacy field in sync
        self.calculate_grade()
        super().save(*args, **kwargs)

    def get_grade_label(self):
        total = float(self.total_score)
        if total >= 70:
            return 'Distinction'
        elif total >= 60:
            return 'Credit'
        elif total >= 50:
            return 'Pass'
        elif total >= 45:
            return 'Pass (Marginal)'
        return 'Fail'


class Fee(models.Model):
    department             = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='fees')
    level                  = models.CharField(max_length=3, choices=LEVEL_CHOICES)
    semester               = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    session                = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    tuition_fee            = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sug_fee                = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lab_fee                = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    course_fee             = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_fees             = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_fees_description = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['department', 'level', 'semester', 'session']
        ordering        = ['level', 'semester']

    def __str__(self):
        return f"{self.department.code} {self.level}L {self.get_semester_display()} - {self.session}"

    def total_amount(self):
        return self.tuition_fee + self.sug_fee + self.lab_fee + self.course_fee + self.other_fees


class FeePayment(models.Model):
    student               = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='fee_payments')
    fee                   = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name='payments')
    amount_paid           = models.DecimalField(max_digits=12, decimal_places=2)
    receipt               = models.FileField(upload_to='receipts/')
    bank_name             = models.CharField(max_length=100, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True)
    payment_date          = models.DateField()
    status                = models.CharField(max_length=20, choices=FEE_STATUS_CHOICES, default='pending')
    verified_by           = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments',
    )
    verified_at  = models.DateTimeField(null=True, blank=True)
    notes        = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.matric_number} - {self.fee} - {self.status}"


class GPAResult(models.Model):
    """Stores calculated GPA for each semester."""

    student            = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='gpa_results')
    session            = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    semester           = models.ForeignKey(Semester, on_delete=models.CASCADE)
    gpa                = models.DecimalField(max_digits=4, decimal_places=2)
    total_credits      = models.IntegerField()
    total_grade_points = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.matric_number} - {self.semester}: GPA {self.gpa}"

    class Meta:
        unique_together = ['student', 'session', 'semester']
        ordering        = ['-session__name', '-semester__semester']


class CourseAllocation(models.Model):
    """Assign lecturers to courses."""

    lecturer       = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_staff': True})
    course         = models.ForeignKey(Course, on_delete=models.CASCADE)
    session        = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    is_coordinator = models.BooleanField(default=False)
    assigned_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lecturer.get_full_name()} - {self.course.code} ({self.session.name})"

    class Meta:
        unique_together = ['lecturer', 'course', 'session']
        ordering        = ['-session__name', 'course__code']
