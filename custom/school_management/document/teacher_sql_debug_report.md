# Teacher Search Panel SQL Error Investigation

Date: 2026-10-02. Odoo 19.0. Database: `odoo`, read from `odoo.conf`.

## Confirmed Root Cause

The Heads of Department action uses `view_university_hod_search`, not the ordinary teacher search view. That search view contains a `managed_department_id` search-panel category and a group-by on that field. The original field definition was a non-stored computed Many2one with no search method, so the search-panel aggregation could not convert it to SQL. The exact reported exception was reproduced in an isolated diagnostic registry with the original non-stored field metadata.

The existing Python edit had not been deployed. Before the upgrade, database field metadata still reported `store=False` and there was no `university_teacher.managed_department_id` column. A fresh registry loaded the edited source with `store=True`, compute `_compute_managed_department_id`, and **no dependencies**. The running HTTP worker PID 3564 started at 09:22:48; `teacher.py` was last edited at 09:42:08. Its command used `--dev xml`, which did not reload that Python edit. Its virtual-environment launcher was PID 29236; these two PIDs were one server, not two competing servers.

The current edit also introduced a separate semantic error: it assigned every teacher's home `department_id` to `managed_department_id`, regardless of whether that teacher held a HOD appointment. `_compute_admin_appointments` also continued assigning the same field, leaving two competing computations.

The analogous dean search view uses non-stored `managed_faculty_id` for its search panel and group-by. The same SQL-conversion exception was independently reproduced for that field, so it received the same scoped correction.

The original live worker's private `_fields` objects were not directly memory-inspected. Its command, start time, source edit time, pre-upgrade database metadata, action/view wiring, and isolated reproduction establish the stale deployment and SQL-incompatible definition. After upgrading and restarting, a fresh registry and the running server use the verified configuration and module location.

## Source And Configuration Inspection

The initial complete IDE project search returned ten `managed_department_id` references, all in two source files:

| File | Original Lines | Use |
| --- | --- | --- |
| `models/teacher.py` | 241, 245 | Field definition and compute name |
| `models/teacher.py` | 403 | Assignment by the old appointments compute |
| `models/teacher.py` | 563, 565 | Current replacement compute and home-department assignment |
| `views/teacher_views.xml` | 284, 468 | Form and HOD list columns |
| `views/teacher_views.xml` | 486 | HOD search field |
| `views/teacher_views.xml` | 492 | HOD department group-by |
| `views/teacher_views.xml` | 497 | HOD search-panel category |

No duplicate field declaration or teacher model override was found. Runtime model source inspection found only `custom/school_management/models/teacher.py` among the module's teacher model classes.

Configured addon roots are `C:\Odoo\odoo\addons`, `C:\Odoo\odoo\odoo\addons`, and `C:\Odoo\odoo\custom`. Odoo also adds `C:\Users\Rith2\AppData\Local\OpenERP S.A.\Odoo\addons\19.0`. Only `C:\Odoo\odoo\custom\school_management` contains this module's manifest in those roots. Recursive inspection under `C:\Odoo` found no other module copy; `static/src/school_management` is an asset directory, not an addon. `get_module_path()` and inspected model method source both resolve to the expected custom module.

Files inspected for this investigation included:

- `odoo.conf`, `start_odoo.ps1`, module `__manifest__.py`, and package initialization files.
- `models/teacher.py`, `models/academic_assignment.py`, `models/department.py`, `models/faculty.py`, and `models/res_users.py`.
- `views/teacher_views.xml`, including all three search views and four teacher actions.
- `security/security.xml`, `security/record_rules.xml`, and `security/ir.model.access.csv`.
- `data/cleanup_legacy_models.xml` and `data/fix_user_teacher_links.xml`, to check upgrade side effects.
- Existing teacher and record-rule tests and startup/upgrade logs.

All module Python and XML files were parsed for syntax. Source searches covered the project, and database inspection covered effective teacher actions, saved filters, search views, inherited-view links, field metadata, and record rules. The database had three teacher search views with no inherited search views, four teacher actions, and one saved filter grouping by `department_id`. No action domain, saved filter, Python search domain, record rule, or access-control definition referencing `managed_department_id` was found. Its SQL uses were the HOD search field, group-by, and search-panel category.

## Record Rules And Permissions

The effective teacher rules were:

```python
# Teacher: own profile
['|', ('user_id', '=', user.id), ('id', '=', user.teacher_id.id)]

# HOD: department teachers
[('department_id.head_id.user_id', '=', user.id)]

# Dean: faculty teachers
[('department_id.faculty_id.dean_id.user_id', '=', user.id)]

# University administrator: all teachers
[(1, '=', 1)]
```

`res.users.teacher_id` links a user to a teacher; `university.teacher.user_id` links a teacher to a login. `department.head_id` and `faculty.dean_id` are stored computations from role assignments. The existing HOD rule follows the department's appointed head and already expresses the intended organizational relationship. Replacing it with a domain using `user.teacher_id.managed_department_id` would introduce different behavior where forward and reverse user links disagree. No security rule or ACL was changed.

## Exact Changes

Production code changed only in `models/teacher.py`. Added regression tests in `tests/test_teacher_managed_scopes.py` and imported them in `tests/__init__.py`. Added this report. The pre-existing `views/teacher_views.xml` formatting edit was preserved and not modified by this investigation. No configuration, permission, menu, or business module was rewritten.

Before, as found in the working tree:

```python
managed_department_id = fields.Many2one(
    "university.department",
    string="Managed Department",
    # compute="_compute_admin_appointments",
    compute = "_compute_managed_department_id",
    store = True,
    index = True,
)

def _compute_managed_department_id(self):
    for teacher in self:
        teacher.managed_department_id = teacher.department_id

managed_faculty_id = fields.Many2one(
    "university.faculty",
    string="Managed Faculty",
    compute="_compute_admin_appointments",
)
```

After:

```python
managed_faculty_id = fields.Many2one(
    "university.faculty",
    string="Managed Faculty",
    compute="_compute_managed_scopes",
    store=True,
    index=True,
)
managed_department_id = fields.Many2one(
    "university.department",
    string="Managed Department",
    compute="_compute_managed_scopes",
    store=True,
    index=True,
)

@api.depends(
    "assignment_ids",
    "assignment_ids.staff_id",
    "assignment_ids.role",
    "assignment_ids.active",
    "assignment_ids.faculty_id",
    "assignment_ids.department_id",
    "assignment_ids.start_date",
)
def _compute_managed_scopes(self):
    for teacher in self:
        # Match the assignment model's ordering independently of cached relation order.
        assignments = teacher.with_context(active_test=False).assignment_ids.sorted(
            key=lambda assignment: (
                assignment.start_date or fields.Date.to_date("0001-01-01"),
                assignment.id or 0,
            ),
            reverse=True,
        )
        dean = assignments.filtered(lambda assignment: assignment.active and assignment.role == "dean")[:1]
        head = assignments.filtered(lambda assignment: assignment.active and assignment.role == "department_head")[:1]
        teacher.managed_faculty_id = dean.faculty_id
        teacher.managed_department_id = head.department_id
```

Removed the obsolete replacement compute and the two managed-scope assignments from `_compute_admin_appointments`; that method continues computing the four appointment-date fields.

## Why This Is Correct

Each record receives both values, including empty recordsets/False when it has no qualifying appointment. Assignment creation, deletion, reassignment, role, activation, scope, and start-date changes invalidate the computations. Start date is included because the assignment model orders appointments by `start_date desc, id desc`; explicit sorting avoids dependence on previously cached One2many ordering. IDs cannot be edited, so no ID dependency is needed. End date does not affect the existing active-flag selection, so it does not affect these scope values.

Stored computes use Odoo's default `compute_sudo=True`, confirmed in runtime metadata. The computation has no current-user, permission, timezone, current-time, or company-context inputs. `active_test` is explicitly normalized, and qualifying assignments are selected through their `active` flags. It therefore represents a stable organizational fact rather than a user-specific result. This follows Odoo's stored compute and dependency mechanism: [Odoo 19 ORM documentation](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html).

The original appointment semantics use the most recent **active** role assignment, not today's date interval. That behavior is preserved; this fix does not introduce automatic expiration or change appointment business rules.

The other search-view fields were reviewed and left unchanged:

| Field | Effective Metadata | Result |
| --- | --- | --- |
| `is_head` | Stored; dependencies include assignment active, role, and staff | SQL filter succeeds |
| `class_count` | Stored; dependencies include section active and teacher | SQL filter succeeds |
| `on_leave` | Non-stored with `_search_on_leave` | SQL filter succeeds through search method |
| `is_present` | Non-stored with `_search_is_present` | SQL filter succeeds through search method |

Presence/leave intentionally remain dynamic because they depend on today's date in the user's context.

## Upgrade And Verification

The database name was read from configuration, not guessed. The identified old server was stopped, and this upgrade/test command completed with exit code 0:

```powershell
cd C:\Odoo\odoo
.\venv\Scripts\python.exe odoo-bin -c odoo.conf -d odoo -u school_management --stop-after-init --max-cron-threads=0 --no-http --test-enable --test-tags /school_management:TestTeacherManagedScopes --logfile=teacher_sql_upgrade.log
```

The ordinary Windows upgrade command is:

```powershell
cd C:\Odoo\odoo
.\venv\Scripts\python.exe odoo-bin -c odoo.conf -d odoo -u school_management --stop-after-init --max-cron-threads=0
```

Stop the server before a future upgrade and restart it afterward. With the venv activated, `python` can replace `.\venv\Scripts\python.exe`. There is no trailing backslash.

Verification results:

- Syntax: all 72 Python files and 65 XML files passed; `git diff --check` passed.
- Module upgrade: succeeded; four regression tests passed with zero failures/errors.
- Runtime fields: both managed scope fields have `store=True`, `compute='_compute_managed_scopes'`, `related=None`, complete dependencies, and `compute_sudo=True`.
- Database: both `ir.model.fields.store` values are true, both SQL columns exist, and all 10 teachers including archived records have stored values matching their role assignments.
- Backend teacher lists, the three effective search views, all four requested filters, position multi-select, managed-scope grouping, and search-panel ranges succeeded for the admin, dean, HOD, and teacher accounts.
- Every returned faculty, department, managed-department, and managed-faculty counter matched a separate `search_count()` under that same user's permissions. The current active HOD domain has no matching records, so its counters are zero; a synthetic appointment regression test confirmed a positive managed-department counter of one.
- All 86 module record-rule domains evaluated and executed against their registered models under the four representative user evaluation contexts.
- Access results were compared before/after for all 13 active internal users: identical. Visible teacher IDs and all four ACL operation flags matched for the nine readable accounts; the same four other accounts remained denied access.
- Live server restarted with the same configuration and `--dev xml`. Launcher PID 26716 and worker PID 11916 are one server; worker 11916 serves port 8070. Login endpoint returned HTTP 200. Startup loaded 131 modules successfully.

Evidence logs: `C:\Odoo\odoo\teacher_sql_upgrade.log` and `C:\Odoo\odoo\teacher_sql_server.log`.

## Remaining Limits And Risks

Browser automation could not initialize because its runtime reported a Windows sandbox helper error. Therefore authenticated browser rendering/click-through was not visually verified; list, view, filter, permissions, grouping, and counter checks were executed through the actual Odoo backend methods. The running login endpoint was independently checked over HTTP.

Existing startup warnings for missing NOT NULL constraints on `res.partner.autopost_bills`, `res.partner.group_rfq`, and `res.partner.group_on` remain outside this fix. Existing role-assignment date/active semantics and mismatched user links, if present in data, are preserved. SQL domains using the four reviewed fields work, but this investigation does not certify every possible custom operator or unrelated compute.

Tests used Odoo transaction rollback; their fixtures were not retained. No existing data was deleted, no database was reset, and no destructive Git operation was used. A future Python edit still requires a server restart because this server retains XML-only development reload.
