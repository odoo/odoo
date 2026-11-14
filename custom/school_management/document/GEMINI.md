# University ERP & School Management — Development Guidelines

## 1. Odoo 19 Framework & Syntax Invariants
- **Views**:
  - Always use `<list>` instead of legacy `<tree>`.
  - Always use `invisible="expr"` instead of deprecated `attrs="{'invisible': ...}"`.
  - In `<search>` views, never add attributes like `expand="0"` to `<group>`. Use bare `<group>` tags.
  - Wrap action buttons in `<header>` and lifecycle state fields in `widget="statusbar"`.
- **Model Constraints**:
  - Do NOT use deprecated `_sql_constraints = [...]`.
  - Define constraints using `_constraint_name = models.Constraint("unique (col1, col2)", "Error message.")`.
- **Model Creation & Stored Computes**:
  - Computed stored fields must have sensible defaults (or `default=lambda self: ...`) if required, preventing Postgres not-null violations on insert.
  - Master data models (`university.academic.year`, `university.faculty`, `university.department`, `university.program`) require mandatory fields (`date_start`, `date_end`, `code`) — always supply them in tests, wizards, and seed data.

## 2. Server Process & Upgrade Discipline
- **Process Management on Windows**:
  - Before running `odoo-bin -u school_management --stop-after-init` or `--test-enable`, ALWAYS terminate running Odoo python processes to prevent Postgres relation lock contention:
    ```powershell
    Get-Process | Where-Object { $_.Path -like "*\Odoo\odoo\venv\*" } | Stop-Process -Force
    ```
  - After upgrading or modifying Python code, launch the background daemon with `IsDaemon: true` and verify HTTP 200 via `curl.exe -I http://localhost:8070/web/login`.

## 3. UI & Design Standards ("Clean UI")
- **Layout**:
  - Responsive 4-column KPI metric card section at the top of main form views (Term GPA, Total Credits, Passed Credits, Academic Standing) with subtle borders, muted labels, and bold statistics.
  - Clean Bootstrap badges (`badge bg-success`, `badge bg-info`, `badge bg-warning`, `badge bg-danger`) for status columns.
  - Inline breakdown tables with row-level passing/failing decorations (`decoration-success="is_passing"`, `decoration-danger="not is_passing"`).
  - Empty states: Provide clean fallback visuals for empty charts and lists instead of broken or 100% false absence states.

## 4. Academic Grading & Attendance Engine
- **Attendance Equivalence Formula (§3.3)**:
  - $\text{effective\_absences} = \text{actual\_absents} + \lfloor\text{permissions}/2\rfloor + \lfloor\text{lates}/4\rfloor$
  - $\text{attendance\_score} = \max(0.0, 10.0 - \text{effective\_absences} \times 1.0)$
  - Attendance entries have unique constraint `(student_id, date, section_id)` — test data must use separate dates.
- **5-Component Weight Rollup (100% Total)**:
  - Attendance (10%) + Quiz (10% averaged across quizzes) + Midterm (20%) + Assignment (10% averaged) + Final Exam (50%).
  - Midterm + Final completion gate: Course evaluation status is "In Progress" until both Midterm and Final exams are completed and published; only then is the letter grade and Term GPA finalized.
  - Academic Standing thresholds: Dean's List ($\ge 3.50$), Good Standing ($\ge 2.00$), Academic Probation ($< 2.00$).

## 5. Automated Testing Rules
- Every grading, exam, or academic feature must have a corresponding test class inheriting from `odoo.tests.common.TransactionCase` registered in `../tests/__init__.py`.
- Run verification tests with:
  ```powershell
  python odoo-bin -c odoo.conf -u school_management --test-enable --test-tags=/school_management:<TestClass> --stop-after-init
  ```
