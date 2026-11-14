# Login Guide — University Management System

How to sign in to the `school_management` addon on the local Odoo 19 instance.

## 1. Start the server

From `C:\Odoo\odoo`:

```powershell
& .\start_odoo.ps1
```

Then open <http://localhost:8070/web/login> in a browser.

The local `odoo.conf` locks Odoo to the single `odoo` database (`dbfilter = ^odoo$`, `list_db = False`), so there is **no database selector** — the login page signs you straight into that database.

## 2. Demo accounts

These accounts exist in the `odoo` database (`admin` is created by Odoo itself; `dean`, `hod`, `teacher`, and `student` are inserted by the SQL seed). **Login names are confirmed; passwords are not stored in the repository** — they were set when each account was created. The only password currently verified against the database hash is `student`.

| Login | Display name (partner) | Role | Groups assigned | Linked record after the link fix | Password status |
|---|---|---|---|---|---|
| `admin` | Administrator | Full access (superuser) | `base.group_system` only — **not** a member of any school group | — | Set at account creation; not the default `admin` in this database |
| `dean` | Head of Faculty | Head of Faculty | School User, Teacher, HOD, Head of Faculty | Teacher **Prof. Charles Xavier** (active Dean of Faculty of Engineering & Technology) | Set at account creation |
| `hod` | Demo HOD | Head of Department | School User, Teacher, HOD | Teacher **Dr. Sarah Jenkins** (active HOD of Department of Clinical Medicine) | Set at account creation |
| `teacher` | Teacher | Teacher | School User, Teacher | Teacher **Dr. Gregory Hous** | Set at account creation |
| `student` | Student | Student (internal) | School User, Student | Student record **Test** (student 6) | **`1234` (verified)** |

The system's functional roles are Student, Teacher/Advisor, Head of Department, Head of Faculty, Registrar, and University Administrator. Create a Registrar account in **Settings -> Users** when one is not included in the local seed.

### What each role can see

- **admin** — University Administrator with full institutional access and an institution-wide dashboard.
- **dean** — Head of Faculty, with faculty-wide information and a faculty dashboard.
- **hod** — Head of Department, with managed-department information and a department dashboard.
- **teacher** — Teacher/Advisor, with assigned classes, advisees, attendance, and follow-up information.
- **student** — personal profile, enrollments, fees, payments, and student dashboard.
- **registrar** — student-record and transcript request queues, with a registrar dashboard. Create this account if it is absent from the demo seed.

After signing in as a user, if access does not match the table above, sign out and back in (record-rule group changes are loaded at login). Verify the user‑to‑teacher link under **Settings -> Users -> the user -> Academic Staff** if it still looks wrong. Until the `-u school_management` upgrade runs, the live database still holds the original (broken) user‑to‑teacher links, so dean/hod/teacher scopes will be smaller than the table shows.

## 3. If you don't know a password

Passwords are stored as one-way PBKDF2-SHA512 hashes and **cannot be recovered**. Do one of the following:

### Option A — reset from the UI (recommended)

1. Log in as `admin`.
2. Open **Settings -> Users** and select the user (`dean`, `hod`, `teacher`, …).
3. Click **Send password reset instructions** (or set a new password directly if the view allows), then sign out and log back in with the new password.

### Option B — reset with the Odoo shell

Stop the server first, then run (from `C:\Odoo\odoo`):

```powershell
& .\venv\Scripts\python.exe .\odoo-bin shell -c .\odoo.conf -d odoo --no-http
```

At the shell prompt:

```python
user = env['res.users'].search([('login', '=', 'dean')], limit=1)
user.write({'password': 'Temporary123!'})
```

Restart the server with `& .\start_odoo.ps1` and log in with the new password.

## 4. Re-creating the supporting data

The teacher, student, faculty, department, and assignment records behind these roles come from the SQL seed (not from a module data file), load it for a fresh database after installing the module:

```powershell
& .\venv\Scripts\python.exe .\custom\school_management\seed\run_seed.py
```

The seed is `ON CONFLICT (id) DO NOTHING`, so re-running it never overwrites existing records. Re-running the seed does **not** restore the forward/reverse user‑teacher links after the fix is applied. The fix is delivered via `data/fix_user_teacher_links.xml` and runs once on upgrade (`-u school_management`); until that upgrade runs, the live database still has the old broken links. An equivalent standalone SQL script is kept at `security/fix_demo_staff_links.sql` if you prefer to apply it directly with `psql`.

## Related documents

- [`local_configuration_guide.md`](local_configuration_guide.md) — install, upgrade, and verification of the addon.
- [`project_overview.md`](project_overview.md) — implemented features, models, and security boundaries.
