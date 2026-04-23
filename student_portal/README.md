# 🎓 Unique Open University — Student Results & Fees Management System

A full-featured Django + Bootstrap web application for managing student academic records and fee payments across all levels and semesters.

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Database Seeding](#database-seeding)
- [Project Structure](#project-structure)
- [User Roles](#user-roles)
- [Deployment](#deployment)

---

## Features

### Student Portal
- Secure registration with department selection
- One-time profile setup (locked after saving — prevents tampering)
- Semester-by-semester results accordion (all levels)
- Automatic semester average: `sum of scores ÷ number of courses`
- Credit hours displayed per course (not factored into averages)
- Fee breakdown per semester with upload status tracking
- Drag-and-drop receipt upload (PDF, JPG, PNG — max 5 MB)
- Confirmation modals before any irreversible action
- Fully responsive Bootstrap 5 design

### Admin Panel (`/admin/`)
- Manage departments, courses, academic sessions
- Upload and edit student results
- Verify or reject fee payments (bulk actions)
- Full student profile management

---


## Local Setup

### Prerequisites
- Python 3.11+
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/student-portal.git
cd student-portal

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment file
cp .env.example .env
# Edit .env and set your SECRET_KEY

# 5. Run migrations
python manage.py makemigrations portal
python manage.py migrate

# 6. Seed initial data
python manage.py seed_data

# 7. Start the development server
python manage.py runserver
```

Visit:
- **Student portal** → http://127.0.0.1:8000/
- **Admin panel**    → http://127.0.0.1:8000/admin/
  - Username: `admin`  |  Password: `admin123` *(change immediately)*

---
---

## Database Seeding

```bash
python manage.py seed_data
# Optional: set a custom admin password
python manage.py seed_data --admin-password mysecurepassword
```

Seeding is **idempotent** — safe to run multiple times without creating duplicates.

What gets seeded:
- 4 academic sessions (2021/2022 → 2024/2025, current = 2024/2025)
- 8 departments (CSC, EEE, BUS, MED, LAW, ACC, CVE, ECO)
- Full course list for Computer Science (100L–400L, both semesters)
- Course list for Business Administration (100L–200L)
- One superuser: `admin`

---

## User Roles

| Feature | Student | Admin |
|---------|---------|-------|
| View results | ✅ | ✅ |
| Upload results | ❌ | ✅ |
| Edit profile after setup | ❌ | ✅ |
| Upload fee receipts | ✅ | ✅ |
| Verify fee payments | ❌ | ✅ |
| Manage departments / courses | ❌ | ✅ |
| Manage academic sessions | ❌ | ✅ |

### Score Performance

| Score | Label |
|-------|-------|
| 70 – 100 | Distinction |
| 60 – 69  | Credit |
| 50 – 59  | Pass |
| 45 – 49  | Pass (Marginal) |
| 0  – 44  | Fail |

---

## Deployment

### Heroku / Railway

```bash
# Set environment variables on your platform dashboard:
SECRET_KEY=<generated-key>
DEBUG=False
ALLOWED_HOSTS=your-app-name.herokuapp.com
DATABASE_URL=<postgres-url-from-platform>
```

### After any deployment

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### Important production checklist

- [ ] `DEBUG=False` in environment
- [ ] Strong, unique `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` set to your actual domain
- [ ] PostgreSQL database connected
- [ ] Admin password changed from default
- [ ] Media files served via cloud storage (S3 / Cloudinary) for scale

---

## License

This project is provided for educational use.
