# Odoo module scan and professional upgrade prompt

Copy everything under "The prompt" into Claude Code (or any coding assistant) opened at the root of your Odoo addons folder. Replace the values in `[brackets]` first.

---

## The prompt

You are a senior Odoo engineer and code reviewer. Your job is to scan my custom Odoo module, find the risks in its business flow, and then upgrade it to a more professional, secure and maintainable standard.

### Context

- Odoo version: [18]
- Module name(s): [university module, e.g. university_management]
- Models to focus on: all models starting with `university.` plus `school.dashboard`
- Main flows: student registration, enrollment (single and bulk), fee invoicing, payments, dashboard reporting
- Users and roles: [admin, registrar, accountant, teacher, student]
- Environment: [production has real data / still in development]

### Ground rules

1. Work in phases. Finish and report each phase before starting the next one.
2. Do not edit any file until I approve the plan in Phase 3.
3. Never guess. If you cannot find something in the code, say "not found" and tell me what you looked for.
4. Every finding must include the file path, the line or method name, and a short quote or description of the evidence.
5. Never use `sudo()` to fix a permission problem. Fix the access rule instead.
6. Do not change field names or model names without also writing a migration script, because that would break existing data.
7. Keep the code style consistent with the rest of the module and with the OCA / Odoo guidelines.

### Phase 1: Scan (read only)

Read the whole module and build an inventory:

- **Models:** every model, its `_name`, `_inherit`, fields, computed fields (stored or not), constraints and state fields.
- **Views and menus:** list, form, kanban, search views, actions, and which menu opens them.
- **Security:** every line in `ir.model.access.csv`, every record rule, every security group. List models that have no access rule.
- **Automation:** `create`, `write`, `unlink` overrides, `onchange` methods, automated actions, cron jobs, wizards, mail templates and sequences.
- **Data flow:** for each main flow, write the chain of models and methods it passes through, step by step.

Output a short table of the inventory. Do not judge anything yet.

### Phase 2: Risk assessment

Check each area below and list every problem you find.

**A. Business flow risks**
- States that cannot be reached, or cannot be left (dead ends).
- Actions that can be run twice (double enrollment, double payment, double posting).
- Missing checks before a state change (for example: can a fee be paid before it is posted? can a student be enrolled while suspended?).
- Records that can be deleted or edited after they are posted or paid.
- Places where money, balances or counts could become inconsistent between models.
- Missing constraints (`@api.constrains` and SQL constraints) for rules that currently exist only in the UI.

**B. Security risks**
- Models with no access rule, or access that is too wide.
- Missing record rules (multi-company, teacher sees only own classes, student sees only own data).
- Use of `sudo()`, raw SQL built with string formatting, or `eval`.
- Buttons and server actions callable by users who should not see them.
- Sensitive fields (grades, fees, personal data) visible to the wrong groups.

**C. Performance risks**
- Non-stored computed fields used in list views, filters or group by.
- Missing `index=True` on fields used in searches and joins.
- `search()`, `browse()`, `create()` or `write()` inside a `for` loop (N+1 problems).
- Computed methods with empty or wrong `@api.depends`.
- Loading full records where `_read_group` or `search_count` is enough.
- Heavy dashboard or report code that runs on every page load.

**D. Data integrity and upgrade risks**
- Fields with no default or no `required` where the code assumes a value.
- `ondelete` behavior on Many2one fields (what happens to child records).
- Missing `_sql_constraints` for unique values (student number, email, invoice number).
- Missing migration scripts or version bumps in `__manifest__.py`.
- Hard-coded ids, names or strings that will break on another database.

**E. Code quality risks**
- Duplicated code, very long methods, unclear names.
- Missing docstrings on business methods.
- Broad `except Exception` that hides real errors.
- Missing translations (`_()` around user-facing strings).
- Missing tests.

For every finding give:

| Field | Content |
|---|---|
| ID | R-01, R-02, ... |
| Area | A, B, C, D or E |
| Severity | Critical / High / Medium / Low |
| Location | file and method |
| Problem | one or two sentences |
| Impact | what can go wrong for the real user |
| Fix | the recommended change |
| Effort | Small / Medium / Large |

Sort the table by severity, then by effort (cheap and important first).

### Phase 3: Upgrade plan (wait for my approval)

Turn the findings into a plan with these groups:

1. **Must fix now** (Critical and High): security holes, data-loss risks, broken flows.
2. **Should fix next** (Medium): performance, constraints, missing indexes.
3. **Professional polish** (Low): naming, docstrings, translations, tests, documentation.

For each group, list the exact files you would change and whether a data migration is needed. Also propose improvements to the flow itself:

- A clear state machine for each main model (draft, confirmed, posted, paid, cancelled), with allowed transitions and who may trigger them.
- Chatter and tracking (`mail.thread`, `tracking=True`) on important models and fields.
- Validation and clear error messages using `ValidationError` and `UserError`.
- Reports and dashboards that respect user permissions.
- Default filters, groupings and sensible search views.

Stop here and ask me which items to implement.

### Phase 4: Implement (only after approval)

For the approved items only:

1. Make small, focused changes, one topic at a time.
2. After each change, explain what changed and why in two or three sentences.
3. Add or update tests (`TransactionCase`) for every business rule you touch. Cover the normal case, the forbidden case and the double-click case.
4. Add migration scripts under `migrations/<version>/` when data or fields change.
5. Bump the module version in `__manifest__.py`.
6. Do not touch files outside the approved list.

### Phase 5: Verify

- Run the module tests: `odoo-bin -d [testdb] -i [module] --test-enable --stop-after-init`.
- Run an upgrade test: `odoo-bin -d [testdb] -u [module] --stop-after-init`.
- List every manual test I should run in the UI, per role.
- Give me a before and after summary: number of findings by severity, and which are fixed, deferred or rejected.

### Output format

- Write the final report as a Markdown file called `SCAN_REPORT.md` in the module folder.
- Use these sections: Summary, Inventory, Findings table, Upgrade plan, Changes made, Test results, Remaining risks.
- Keep the language simple and direct. Explain technical terms the first time you use them.

---

## Before you run it

- Back up the database and commit the code to Git, so every change can be undone.
- Run it on a test database with a copy of real data, not on production.
- If the module is large, run one phase per session and give the assistant the previous phase's report as input.

## Optional add-ons

Paste any of these under "Context" when they apply:

- "Focus only on the fee and payment flow. Ignore academic records."
- "This system will be used by 5,000 students. Judge performance for that size."
- "We must support Khmer and English. Check translations and RTL/LTR issues."
- "Compare our flow with standard Odoo accounting (`account.move`, `account.payment`) and tell me where we should reuse it instead of custom models."
