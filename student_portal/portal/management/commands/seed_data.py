"""
Management command: seed_data
Populates the database with initial departments, courses and academic sessions.
Safe to run multiple times — uses get_or_create throughout.

Usage:
    python manage.py seed_data
    python manage.py seed_data --admin-password mypassword
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from portal.models import (
    Faculty, Department, Course, AcademicSession, Semester,
    StudentProfile, Result, Fee
)


class Command(BaseCommand):
    help = 'Seeds initial departments, courses and academic sessions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-password',
            default='admin123',
            help='Password for the auto-created superuser (default: admin123)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== UniPortal Database Seeder ===\n'))

        faculties = self._seed_faculties()
        sessions, semesters = self._seed_sessions_and_semesters()
        departments = self._seed_departments(faculties)
        self._seed_courses(departments)
        self._seed_fees(departments, sessions['current'])
        self._seed_superuser(options['admin_password'])
        self._seed_sample_student(departments, sessions['current'], semesters['current'])

        self.stdout.write(self.style.SUCCESS('\n✓ Database seeded successfully!\n'))

    def _seed_faculties(self):
        faculties_data = [
            {'name': 'Faculty of Science', 'code': 'FOS', 'dean': 'Prof. John Smith'},
            {'name': 'Faculty of Engineering', 'code': 'FOE', 'dean': 'Prof. Sarah Johnson'},
            {'name': 'Faculty of Management Sciences', 'code': 'FMS', 'dean': 'Dr. Michael Brown'},
            {'name': 'Faculty of Social Sciences', 'code': 'FSS', 'dean': 'Prof. Emily Davis'},
            {'name': 'Faculty of Arts', 'code': 'FOA', 'dean': 'Dr. Robert Wilson'},
        ]
        self.stdout.write('  Faculties...')
        faculties = {}
        for f in faculties_data:
            faculty, created = Faculty.objects.get_or_create(code=f['code'], defaults=f)
            faculties[f['code']] = faculty
            if created:
                self.stdout.write(f'    + {faculty.name}')
        return faculties

    def _seed_sessions_and_semesters(self):
        sessions_data = [
            {'name': '2023/2024', 'start_year': 2023, 'end_year': 2024, 'is_current': False,
             'start_date': date(2023, 9, 1), 'end_date': date(2024, 8, 31)},
            {'name': '2024/2025', 'start_year': 2024, 'end_year': 2025, 'is_current': True,
             'start_date': date(2024, 9, 1), 'end_date': date(2025, 8, 31)},
        ]
        self.stdout.write('  Academic sessions...')
        sessions = {}
        semesters = {}
        for s in sessions_data:
            session, created = AcademicSession.objects.get_or_create(
                name=s['name'], defaults=s
            )
            sessions['current' if s['is_current'] else 'past'] = session
            if created:
                self.stdout.write(f'    + {s["name"]}')
            
            for sem_name, start_month, end_month in [
                ('First', 9, 1), ('Second', 2, 6)
            ]:
                sem_start = date(s['start_year'] if sem_name == 'First' else s['end_year'], 
                                start_month, 1)
                sem_end = date(s['start_year'] if sem_name == 'First' else s['end_year'],
                              end_month, 28 if end_month == 2 else 30)
                
                semester, created = Semester.objects.get_or_create(
                    session=session,
                    semester=sem_name,
                    defaults={
                        'start_date': sem_start,
                        'end_date': sem_end,
                        'is_current': s['is_current'] and sem_name == 'First',
                        'registration_start': sem_start - timedelta(days=30),
                        'registration_end': sem_start + timedelta(days=14),
                    }
                )
                if s['is_current'] and sem_name == 'First':
                    semesters['current'] = semester
                if created:
                    self.stdout.write(f'      + {semester}')
        
        return sessions, semesters

    def _seed_departments(self, faculties):
        departments_data = [
            {'name': 'Computer Science', 'code': 'CSC', 'faculty': 'FOS', 'duration_years': 4, 'hod': 'Dr. Alan Turing'},
            {'name': 'Electrical Engineering', 'code': 'EEE', 'faculty': 'FOE', 'duration_years': 5, 'hod': 'Prof. Nikola Tesla'},
            {'name': 'Business Administration', 'code': 'BUS', 'faculty': 'FMS', 'duration_years': 4, 'hod': 'Dr. Peter Drucker'},
            {'name': 'Economics', 'code': 'ECO', 'faculty': 'FSS', 'duration_years': 4, 'hod': 'Prof. Adam Smith'},
            {'name': 'English', 'code': 'ENG', 'faculty': 'FOA', 'duration_years': 4, 'hod': 'Dr. Jane Austen'},
            {'name': 'Mathematics', 'code': 'MTH', 'faculty': 'FOS', 'duration_years': 4, 'hod': 'Prof. Carl Gauss'},
            {'name': 'Accounting', 'code': 'ACC', 'faculty': 'FMS', 'duration_years': 4, 'hod': 'Dr. Luca Pacioli'},
        ]
        self.stdout.write('  Departments...')
        departments = {}
        for d in departments_data:
            dept, created = Department.objects.get_or_create(
                code=d['code'], 
                defaults={
                    'name': d['name'],
                    'faculty': faculties[d['faculty']],
                    'duration_years': d['duration_years'],
                    'hod': d['hod'],
                }
            )
            departments[d['code']] = dept
            if created:
                self.stdout.write(f'    + {dept.name}')
        return departments

    def _seed_courses(self, departments):
        self.stdout.write('  Courses...')
        
        csc_courses = [
            ('CSC101', 'Introduction to Computer Science', 3, '100', 'First'),
            ('CSC102', 'Programming in Python', 3, '100', 'Second'),
            ('MTH101', 'General Mathematics I', 3, '100', 'First'),
            ('MTH102', 'General Mathematics II', 3, '100', 'Second'),
            ('PHY101', 'General Physics I', 3, '100', 'First'),
            ('PHY102', 'General Physics II', 3, '100', 'Second'),
            ('GST101', 'Use of English I', 2, '100', 'First'),
            ('GST102', 'Use of English II', 2, '100', 'Second'),
            ('CSC201', 'Data Structures', 3, '200', 'First'),
            ('CSC202', 'Algorithms', 3, '200', 'Second'),
            ('CSC203', 'Computer Organization', 3, '200', 'First'),
            ('CSC204', 'Discrete Mathematics', 3, '200', 'Second'),
            ('CSC205', 'Object-Oriented Programming', 3, '200', 'First'),
            ('CSC206', 'Database Systems', 3, '200', 'Second'),
            ('CSC301', 'Operating Systems', 3, '300', 'First'),
            ('CSC302', 'Computer Networks', 3, '300', 'Second'),
            ('CSC303', 'Software Engineering', 3, '300', 'First'),
            ('CSC304', 'Web Development', 3, '300', 'Second'),
            ('CSC305', 'Artificial Intelligence', 3, '300', 'First'),
            ('CSC306', 'Cybersecurity', 3, '300', 'Second'),
            ('CSC401', 'Machine Learning', 3, '400', 'First'),
            ('CSC402', 'Cloud Computing', 3, '400', 'Second'),
            ('CSC403', 'Mobile Development', 3, '400', 'First'),
            ('CSC499', 'Final Year Project', 6, '400', 'Second'),
        ]
        
        created_count = 0
        for code, title, credits, level, semester in csc_courses:
            dept_code = code[:3] if code[:3] in departments else 'CSC'
            _, created = Course.objects.get_or_create(
                department=departments[dept_code],
                code=code,
                level=level,
                semester=semester,
                defaults={
                    'title': title,
                    'credit_units': credits,
                }
            )
            if created:
                created_count += 1
        
        bus_courses = [
            ('BUS101', 'Introduction to Business', 3, '100', 'First', 'BUS'),
            ('BUS102', 'Business Communication', 3, '100', 'Second', 'BUS'),
            ('ACC101', 'Principles of Accounting I', 3, '100', 'First', 'ACC'),
            ('ACC102', 'Principles of Accounting II', 3, '100', 'Second', 'ACC'),
            ('ECO101', 'Microeconomics', 3, '100', 'First', 'ECO'),
            ('ECO102', 'Macroeconomics', 3, '100', 'Second', 'ECO'),
        ]
        
        for code, title, credits, level, semester, dept in bus_courses:
            if dept in departments:
                _, created = Course.objects.get_or_create(
                    department=departments[dept],
                    code=code,
                    level=level,
                    semester=semester,
                    defaults={
                        'title': title,
                        'credit_units': credits,
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(f'    + {created_count} courses added')

    def _seed_fees(self, departments, session):
        self.stdout.write('  Fee structures...')
        created_count = 0
        
        for dept_code, dept in departments.items():
            for level in dept.get_levels():
                for semester in ['First', 'Second']:
                    fee, created = Fee.objects.get_or_create(
                        department=dept,
                        level=level,
                        semester=semester,
                        session=session,
                        defaults={
                            'tuition_fee': Decimal('50000.00'),
                            'sug_fee': Decimal('2000.00'),
                            'lab_fee': Decimal('5000.00') if dept_code in ['CSC', 'EEE'] else Decimal('0.00'),
                            'course_fee': Decimal('3000.00'),
                            'other_fees': Decimal('1000.00'),
                            'other_fees_description': 'Library and ICT',
                        }
                    )
                    if created:
                        created_count += 1
        
        self.stdout.write(f'    + {created_count} fee structures added')

    def _seed_superuser(self, password):
        self.stdout.write('  Superuser...')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@uniportal.edu', password)
            self.stdout.write(f'    + Created: username=admin')
            self.stdout.write(
                self.style.WARNING(
                    '    ⚠  Change the admin password immediately after first login!'
                )
            )
        else:
            self.stdout.write('    • admin already exists — skipped')

    def _seed_sample_student(self, departments, session, semester):
        self.stdout.write('  Sample student...')
        
        username = '22/12345678'
        
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': 'David',
                'last_name': 'Oche',
                'email': 'john.doe@students.uniportal.edu',
            }
        )
        if user_created:
            user.set_password('student123')
            user.save()
        
        profile, profile_created = StudentProfile.objects.get_or_create(
            user=user,
            matric_number=username,
            defaults={
                'department': departments['CSC'],
                'current_level': '300',
                'current_semester': 'First',
                'current_session': session,
                'entry_year': '2022',
                'mode_of_entry': 'UTME',
                'phone': '08012345678',
                'address': '123 Campus Road, University Town',
                'date_of_birth': date(2004, 5, 15),
                'profile_completed': True,
            }
        )
        
        if profile_created:
            courses = Course.objects.filter(
                department=departments['CSC'],
                level='100'
            )[:6]
            
            for course in courses:
                Result.objects.get_or_create(
                    student=profile,
                    course=course,
                    session=session,
                    semester=semester,
                    defaults={
                        'ca_score': Decimal('25'),
                        'exam_score': Decimal('55'),
                        'status': 'published',
                    }
                )
            
            self.stdout.write(f'    + Created student: {username} / student123')
            self.stdout.write(f'      Level: 300L Computer Science')
        else:
            self.stdout.write('    • Sample student already exists — skipped')