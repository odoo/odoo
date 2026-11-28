# 🎓 University Management System --- Full Architecture

> **Implementation status (2026-09-10):** this document is the conceptual target
> design. The current addon implements structure, people, academic calendar,
> class sections, enrollment, timetables, lesson plans, assignments, attendance,
> grading/assessment, report cards, transcripts, fees, payments, dashboards, and
> role-based security. Not yet implemented: schedule `university.schedule`,
> exams, scholarships, graduation/certificates, and the portal pages
> (`views/portal_templates.xml` is a placeholder). For the authoritative, model
> by-model status list use [`project_structure.md.md`](project_structure.md.md).

The key idea is: **Student is not the whole system. Academic structure,
enrollment, subjects, semesters, exams, results, fees, and users all
interact.**

## 1. 🏛️ University Structure

``` text
University
│
├── Faculty
│      │
│      └── Department
│              │
│              └── Program
│                      │
│                      └── Subject
```

Example:

``` text
Royal University
│
├── Faculty of IT
│   │
│   ├── Department of Computer Science
│   │   └── Bachelor of Computer Science
│   │
│   └── Department of Information Technology
│       └── Bachelor of IT
│
└── Faculty of Business
    │
    ├── Department of Accounting
    └── Department of Management
```

### Odoo models

``` text
university.faculty
university.department
university.program
university.subject
```

## 2. 👨‍🎓 Student Architecture

Student should contain **identity**, not everything.

``` text
university.student
│
├── Student ID
├── Name
├── Photo
├── Gender
├── Date of Birth
│
├── Contact Information
│   ├── Phone
│   ├── Email
│   └── Address
│
├── Emergency Contact
│
├── Academic Information
│   ├── Program
│   ├── Department
│   ├── Academic Year
│   └── Current Semester
│
└── Status
    ├── Active
    ├── Suspended
    ├── Graduated
    └── Dropped
```

**Important:** Don't put semester, subject, exam, fee, and result
directly as simple fields on Student. Those are separate business
records.

## 3. 📚 Academic Structure

``` text
Faculty
   ↓
Department
   ↓
Program
   ↓
Subject
```

Example:

``` text
Faculty of IT
     ↓
Computer Science Department
     ↓
Bachelor of Computer Science
     ↓
Year 3
     ↓
Semester 1
     ↓
Database Management
```

## 4. 📅 Academic Year & Semester

Create:

``` text
university.academic.year
university.semester
```

Example:

``` text
Academic Year
2026 - 2027
│
├── Semester 1
│
└── Semester 2
```

This is important because a student's academic data changes over time.

## 5. 📝 Enrollment

Don't connect Student directly to Subject with a simple Many2many.

Instead create an **Enrollment** model.

``` text
university.enrollment
```

Relationship:

``` text
Student
   │
   └── Enrollment
          │
          ├── Academic Year
          ├── Semester
          ├── Program
          └── Subjects
```

Example:

``` text
Sothearith
│
└── Enrollment 2026 / Semester 1
      │
      ├── Database
      ├── Java
      ├── Web Development
      └── Software Engineering
```

This gives you historical records.

## 6. 👨‍🏫 Teacher Architecture

``` text
university.teacher
│
├── Employee Information
├── Teacher ID
├── Name
├── Email
├── Phone
│
├── Department
│
└── Subjects
```

A teacher can teach multiple subjects.

## 7. 🏫 Class / Section

A **subject** and a **class section** should be different concepts.

``` text
Subject:
Database Management
```

Could have:

``` text
Database Management
│
├── Section A
│   └── Teacher: Mr. Dara
│
├── Section B
│   └── Teacher: Mr. Kim
│
└── Section C
    └── Teacher: Ms. Lina
```

Model:

``` text
university.class.section
```

## 8. 🕐 Class Schedule

``` text
university.schedule
```

Example:

``` text
Monday
│
├── 8:00 - 10:00
│   Database
│   Room: A101
│
├── 10:00 - 12:00
│   Java
│   Room: B201
│
└── 1:00 - 3:00
    Web Development
    Room: Lab 1
```

Relationships:

``` text
Schedule
├── Subject
├── Teacher
├── Classroom
├── Day
├── Start Time
└── End Time
```

## 9. 📅 Attendance

Attendance should be its own transaction.

``` text
university.attendance
```

Example:

``` text
Student       Subject       Date        Status
------------------------------------------------
Sothearith    Database      28/08       Present
Dara          Database      28/08       Absent
Kim           Database      28/08       Late
```

Possible status:

``` text
Present
Absent
Late
Excused
```

## 10. 📝 Examination Architecture

Don't make one `exam` record contain everything.

Use:

``` text
Exam
  ↓
Exam Schedule
  ↓
Exam Result
```

Example:

``` text
Midterm Examination
│
├── Database
│   └── 20 Aug
│
├── Java
│   └── 22 Aug
│
└── Web Development
    └── 25 Aug
```

## 11. 📊 Result Architecture

``` text
Student
   │
   ↓
Enrollment
   │
   ↓
Subject
   │
   ↓
Assessment
   │
   ├── Assignment
   ├── Midterm
   ├── Final
   └── Project
   │
   ↓
Result
```

Example:

``` text
Sothearith
│
└── Database
     │
     ├── Assignment    18/20
     ├── Midterm       25/30
     ├── Final         42/50
     │
     └── Total         85/100
                         ↓
                       Grade A
                         ↓
                       GPA 4.0
```

## 12. 🎯 Grade System

Create:

``` text
university.grade
```

Example:

  Score    Grade     GPA
  -------- ------- -----
  90-100   A         4.0
  85-89    B+        3.5
  80-84    B         3.0
  75-79    C+        2.5
  70-74    C         2.0
  60-69    D         1.0
  \<60     F         0.0

Then calculate:

``` text
Semester GPA
       ↓
Cumulative GPA
       ↓
Academic Standing
```

## 13. 💰 Fee Architecture

Fees should also be transactions.

``` text
Student
   │
   ↓
Fee Invoice
   │
   ├── Tuition
   ├── Registration
   ├── Library
   ├── Laboratory
   └── Other
          │
          ↓
       Payment
```

Example:

``` text
Invoice #INV-001

Tuition             $500
Registration         $50
Library               $20
-------------------------
Total                $570

Paid                 $570
Balance                $0
```

Later you can integrate Odoo's accounting functionality rather than
rebuilding an accounting system yourself.

### Integration with Odoo Standard Accounting & Analytic Accounts

When transitioning or bridging custom fees (`university.fee`) with standard Odoo accounting, the system leverages Odoo's core `account` and `account.analytic.account` infrastructure (`addons/account/models/account_analytic_account.py`):

``` text
Academic Entity (Faculty / Department / Program)
   │
   ↓
Analytic Account (`account.analytic.account`)
   │
   ├── Student Fee Invoices (`account.move.line`) ──► analytic_distribution (Revenue)
   └── Vendor Bills / Operating Costs (`account.move.line`) ──► analytic_distribution (Cost)
```

#### 1. Departmental & Academic Cost Centers
- **Analytic Mapping:** Each `university.faculty`, `university.department`, or `university.program` can be mapped to an `account.analytic.account` (or analytic plan).
- **Analytic Distribution:** When student fee lines (`university.fee.line` / `account.move.line`) are confirmed and posted, revenue is tagged with the corresponding academic entity's analytic account using Odoo 19's `analytic_distribution` dictionary (e.g., `{"<analytic_account_id>": 100.0}`).

#### 2. Capabilities from Standard `account_analytic_account.py`
Standard Odoo `account.analytic.account` (`addons/account/models/account_analytic_account.py`) extends analytic accounts with built-in invoice and vendor bill synchronization:
- **`invoice_count`:** Dynamically aggregates all posted customer invoices / student receipts (`account.move` with sale move types) associated with this analytic account via `analytic_distribution`.
- **`vendor_bill_count`:** Aggregates all posted supplier bills / departmental operational expenses (`account.move` with purchase move types) allocated to the analytic account.
- **Smart Actions:**
  - `action_view_invoice()`: Provides instant drill-down to examine all student invoices and fee receipts attributed to the faculty or program.
  - `action_view_vendor_bill()`: Provides instant access to procurement, instructor contractor costs, and departmental vendor bills.

#### 3. Financial Visibility & P&L per Academic Unit
By linking `university.fee` entries to `account.analytic.account`:
- University management gains direct profitability and cost-center reporting per department, semester, or academic program without creating complex custom accounting ledgers.
- Academic administrators can inspect live revenue collections alongside faculty operating expenses directly from the standard Analytic Accounts view.

## 14. 🎓 Scholarship

``` text
university.scholarship
```

Relationship:

``` text
Student
   ↓
Scholarship
   ├── Type
   ├── Percentage
   ├── Amount
   ├── Start Date
   └── End Date
```

Example:

``` text
Tuition:       $500
Scholarship:    50%
------------------
Pay:           $250
```

## 15. 🎓 Graduation

A university system should eventually have:

``` text
university.graduation
```

Flow:

``` text
Student
   ↓
Complete Required Subjects
   ↓
Earn Required Credits
   ↓
Meet GPA Requirement
   ↓
Graduation
   ↓
Certificate
```

Example:

``` text
Student: Sothearith Kim

Program: Bachelor of IT

Required Credits: 120
Completed Credits: 120

GPA: 3.42

Status: Eligible for Graduation
```

## 16. 🏠 Classroom

``` text
university.building
       ↓
university.classroom
```

Example:

``` text
Building A
│
├── A101
├── A102
└── A103

Building B
│
├── B201
└── B202
```

Classrooms can contain:

``` text
Room Number
Capacity
Building
Type
Equipment
```

## 17. 👥 User & Security Architecture

Because this is Odoo, think about **users and access rights**.

``` text
                    ODOO USERS
                        │
       ┌────────────────┼────────────────┐
       ↓                ↓                ↓
    Student          Teacher            Admin
       │                │                │
       ↓                ↓                ↓
 View own          Manage classes     Full access
 results           Attendance
 fees              Results
 schedule
```

Roles could be:

``` text
University Admin
Faculty Admin
Department Manager
Teacher
Student
Accountant
Registrar
```

## 18. 📊 Dashboard

Your main dashboard can show:

``` text
┌─────────────────────────────────────────────────────┐
│              UNIVERSITY DASHBOARD                   │
├────────────┬────────────┬────────────┬──────────────┤
│ Students   │ Teachers   │ Programs   │ Departments  │
│   5,240    │    320     │    25      │      12      │
├────────────┴────────────┴────────────┴──────────────┤
│                                                     │
│ 📊 Student Statistics                               │
│                                                     │
│ Active        4,850                                 │
│ Graduated       320                                 │
│ Suspended        40                                 │
│                                                     │
├────────────────────────┬────────────────────────────┤
│ 📅 Today's Classes     │ 💰 Fee Status              │
│                        │                            │
│ 45 Classes             │ Paid       $125K           │
│ 12 Exams               │ Unpaid      $18K           │
│ 86% Attendance         │ Scholarship $32K           │
└────────────────────────┴────────────────────────────┘
```

## 🧩 Complete Model Architecture

``` text
UNIVERSITY
│
├── 🏛️ ORGANIZATION
│   ├── Faculty
│   ├── Department
│   ├── Program
│   └── Academic Year
│
├── 👨‍🎓 PEOPLE
│   ├── Student
│   ├── Teacher
│   ├── Staff
│   └── Guardian
│
├── 📚 ACADEMIC
│   ├── Subject
│   ├── Semester
│   ├── Enrollment
│   ├── Class Section
│   └── Academic Credit
│
├── 🕐 SCHEDULE
│   ├── Building
│   ├── Classroom
│   └── Schedule
│
├── 📅 ATTENDANCE
│   └── Attendance
│
├── 📝 EXAMINATION
│   ├── Exam
│   ├── Exam Schedule
│   ├── Assessment
│   ├── Result
│   └── Grade
│
├── 💰 FINANCE
│   ├── Fee
│   ├── Invoice
│   ├── Payment
│   └── Scholarship
│
├── 🎓 GRADUATION
│   ├── Graduation
│   ├── Certificate
│   └── Transcript
│
└── 🔐 SECURITY
    ├── Admin
    ├── Teacher
    ├── Student
    ├── Accountant
    └── Registrar
```

## 🔗 Core ERD

``` text
Faculty
   │
   ↓
Department
   │
   ↓
Program
   │
   ├───────────────┐
   ↓               ↓
Subject         Student
   │               │
   │               ↓
   │          Enrollment
   │               │
   │               ↓
   │          Class Section
   │               │
   ├───────────────┤
   ↓               ↓
Schedule       Attendance
   │
   ↓
Exam
   │
   ↓
Result
   │
   ↓
Grade
   │
   ↓
GPA

Student ─────── Fee ─────── Payment
   │
   └────────── Scholarship

Student ─────── Graduation ─────── Certificate
```

## ⭐ Core Mental Model

Think of the system as **five layers**:

``` text
1. STRUCTURE
   Faculty → Department → Program → Subject

2. PEOPLE
   Student → Teacher → Staff

3. ACADEMIC ACTIVITY
   Enrollment → Class → Schedule → Attendance

4. ASSESSMENT
   Exam → Assessment → Result → Grade → GPA

5. MONEY
   Fee → Invoice → Payment → Scholarship
```

## 🚀 Recommended Implementation Order

Don't implement everything at once.

### Phase 1 --- Foundation

``` text
Student
Faculty
Department
Program
Subject
```

### Phase 2 --- Academic

``` text
Academic Year
Semester
Enrollment
Class Section
Teacher
```

### Phase 3 --- Academic Operations

``` text
Classroom
Schedule
Attendance
```

### Phase 4 --- Examination

``` text
Exam
Assessment
Result
Grade
GPA
```

### Phase 5 --- Finance

``` text
Fee
Invoice
Payment
Scholarship
Analytic Accounting (Cost Centers)
```

### Phase 6 --- Graduation

``` text
Graduation
Certificate
Transcript
```

### Phase 7 --- Dashboard & Security

``` text
Dashboard
KPI Cards
Charts
Reports
Access Rights
User Roles
```

The goal is to build this progressively so each Odoo concept is
understandable rather than copying a huge project all at once.
