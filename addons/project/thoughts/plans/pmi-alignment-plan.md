# PMI Terminology Alignment Plan — Project Module

## Executive Summary

The Odoo project module conflates three distinct project management concepts under
inconsistent naming. This plan aligns the module's terminology with PMI/PMBOK
standards while preserving backward compatibility through database migration scripts.

**Core Problem**: The module uses "stage" to mean three different things:
1. A **workflow step** in a project pipeline (Kanban column)
2. A **task state** (approval/completion/dependency status)
3. A **personal triage bucket** (user's time-horizon categorization)

PMI/PMBOK defines precise, non-overlapping terms for each concept. This plan
adopts those definitions.

---

## 1. PMI Reference Terminology

| PMI Term | PMBOK Definition | Odoo Current | Odoo Proposed |
|----------|-----------------|--------------|---------------|
| **Phase** | "A collection of logically related project activities that culminates in the completion of one or more deliverables." | `project.project.stage` | Keep as-is (project lifecycle) |
| **Workflow State** | The column/position of a work item on a Kanban board. Represents WHERE in the process the item sits. | `project.task.stage_id` → `project.task.type` | Rename to align (see §3) |
| **Status** | The current condition of a project element — a judgment/report ("on track", "at risk"). | `project.update.status` / `last_update_status` | Already correct |
| **State** | The internal condition of a work item (blocked, approved, done). | `project.task.state` | Refine values (see §4) |
| **Milestone** | "A significant point or event in a project." Zero duration. | `project.milestone` | Already correct |
| **Activity** | "A distinct, scheduled portion of work." The formal PMI term for what Odoo calls "task." | `project.task` | Keep "task" (industry standard) |
| **Logical Relationship** | "A dependency between two activities." Types: FS, FF, SS, SF. | `depend_on_ids` / `dependent_ids` | Rename fields (see §5) |
| **Priority** | Relative importance used to determine sequencing. PMI favors ordinal ranking. | `priority` (0-3 categorical) | Refine labels (see §6) |

---

## 2. Conceptual Model (Target State)

```
project.project
├── phase_id (M2O → project.phase)           # Project lifecycle phase
├── status (Selection: on_track/at_risk/...)  # Project health status
├── milestone_ids (O2M → project.milestone)   # Key deliverable dates
└── workflow_ids (M2M → project.workflow.step) # Available workflow steps

project.task
├── step_id (M2O → project.workflow.step)     # Kanban column position
├── state (Selection: in_progress/...)        # Internal condition
├── triage_id (M2O → project.triage)          # Personal time-horizon bucket
├── priority (Selection: 0-3)                 # Urgency ranking
├── milestone_id (M2O → project.milestone)    # Linked milestone
├── predecessor_ids (M2M → project.task)      # "Blocked by" (FS deps)
└── successor_ids (M2M → project.task)        # "Blocks" (FS deps)
```

---

## 3. Workflow Steps (Currently: "Task Stages")

### Problem

`project.task.type` is a **god model** serving two incompatible purposes:
- Shared workflow steps (when `user_id` is null, `project_ids` is set)
- Personal triage buckets (when `user_id` is set, `project_ids` is empty)

The constraint at line 279 is a code smell:
```python
@api.constrains("user_id", "project_ids")
def _check_personal_stage_not_linked_to_projects(self):
    # "A personal stage cannot be linked to a project"
```

Two unrelated concepts forced into one table, then constrained apart.

### Plan

#### Phase 3A: Split `project.task.type` into two new models (keep original)

**`project.task.type` is RETAINED** as a backward-compatibility shim. It
continues to exist in the database with its original table (`project_task_type`)
and all existing data. This ensures:
- Third-party modules referencing `project.task.type` continue to work
- No data migration of the original table is needed initially
- The deprecation can be finalized in a future release when all dependents migrate

**New model: `project.workflow.step`** (canonical model for shared workflow steps)
- Stores: `name`, `sequence`, `fold`, `color`, `project_ids`
- Stores: `mail_template_id`, `rating_template_id`, `auto_update_state` (renamed)
- Stores: `rotting_threshold_days`, `sms_template_id`
- Does NOT have `user_id`
- Table: `project_workflow_step` (new)
- **Sync strategy**: On creation, data is written to BOTH `project.workflow.step`
  AND `project.task.type` (with `user_id=False`). Reads come from the new model.
  This keeps the legacy table populated for any code still reading it directly.

**New model: `project.triage`** (canonical model for personal triage buckets)
- Stores: `name`, `sequence`, `fold`, `user_id`
- Does NOT have `project_ids`, `rating_*`, `mail_template_id`
- Table: `project_triage` (new)
- Default values: Inbox, Today, This Week, This Month, Later, Done, Cancelled
- **Sync strategy**: Same as above — writes propagate to `project.task.type`
  (with `user_id` set) for backward compatibility.

**`project.task.type` compatibility layer**:
```python
class ProjectTaskType(models.Model):
    _name = "project.task.type"
    _description = "Task Stage (Deprecated — use project.workflow.step or project.triage)"

    # All existing fields remain.
    # Mark model with deprecation warning in _description and _logger.
    # Add @api.model_create_multi override that logs deprecation warning
    # when called directly (not via sync from new models).
```

**Initial data population** (in migration script):
- Copy records with `user_id` IS NULL → `project.workflow.step`
- Copy records with `user_id` IS NOT NULL → `project.triage`
- Original `project_task_type` rows are NOT deleted or modified

#### Phase 3B: New fields on `project.task` (keep old as aliases)

| New Field (canonical) | Old Field (kept as alias) | Target Model | Rationale |
|-----------------------|--------------------------|--------------|-----------|
| `step_id` → `project.workflow.step` | `stage_id` → computed alias that reads/writes `step_id` via mapping | `project.workflow.step` | PMI: workflow state = column position. "Step" is concrete. |
| `triage_id` → `project.triage` | `personal_stage_type_id` → computed alias | `project.triage` | Personal prioritization buckets, not workflow steps. |
| `personal_triage_id` → `project.task.triage` | `personal_stage_id` → computed alias | `project.task.triage` | Junction model with clearer naming. |
| `triage_ids` (M2M) | `personal_stage_type_ids` → computed alias | `project.triage` | Plural accessor |

**Alias implementation**: Old fields become `compute`/`inverse` wrappers that
delegate to the new canonical fields. They are marked with
`@api.deprecated("19.0", "Use step_id / triage_id instead")` and retain
`store=False` (the new fields are the stored ones). This means:
- All existing code referencing `stage_id` continues to work
- New code uses `step_id` / `triage_id`
- `stage_id` triggers a deprecation log on access (optional, can be noisy)

#### Phase 3C: Simplify personal triage junction

**Current**: `project.task.stage.personal` with:
- `task_id` → `project.task`
- `user_id` → `res.users`
- `stage_id` → `project.task.type`

**Proposed**: `project.task.triage` (NEW model, parallel to old) with:
- `task_id` → `project.task`
- `user_id` → `res.users`
- `triage_id` → `project.triage`

**`project.task.stage.personal` is RETAINED** with its original table
(`project_task_user_rel`) for backward compatibility. The new
`project.task.triage` uses a new table (`project_task_triage`). A migration
script copies existing data. Both models coexist until deprecation is finalized.

#### Phase 3D: New fields on `project.project` (keep old as aliases)

| New Field (canonical) | Old Field (kept as alias) | Rationale |
|-----------------------|--------------------------|-----------|
| `workflow_step_ids` (M2M → `project.workflow.step`) | `type_ids` → computed alias | "type_ids" was always misleading for "available stages" |
| `phase_id` (M2O → `project.phase`) | `stage_id` → computed alias | PMI term for project lifecycle |

#### Phase 3E: Deprecation Timeline

| Milestone | Action |
|-----------|--------|
| **v19.0** (this release) | New models + fields created. Old models + fields kept as aliases. All new project-module code uses new names. |
| **v19.0 + 6 months** | Dependent modules (enterprise, addons_custom) migrated to new names. Old aliases emit deprecation warnings in logs. |
| **v20.0** (next major) | Old models (`project.task.type`, `project.task.stage.personal`) and old fields (`stage_id`, `personal_stage_type_id`) removed. Migration scripts drop old tables/columns. |

---

## 4. Task State (Currently: `state` field)

### Problem

The `state` field has:
- Inconsistent value prefixes (`01_`, `02_`, `03_`, `04_` vs `1_`)
- A vestigial suffix (`04_waiting_normal` — `_normal` from old `kanban_state`)
- Approval semantics mixed with dependency-blocking semantics
- `date_last_stage_update` that tracks state changes too

### Plan

#### Phase 4A: Clean up state values

| Current Value | Proposed Value | Rationale |
|---------------|---------------|-----------|
| `01_in_progress` | `in_progress` | Drop numeric prefix. Ordering is handled by field definition order, not value sorting. |
| `02_changes_requested` | `changes_requested` | Drop numeric prefix |
| `03_approved` | `approved` | Drop numeric prefix |
| `04_waiting_normal` | `blocked` | PMI term. Drop `_normal` vestige. "Waiting" is vague; "blocked" is precise — the task cannot proceed. |
| `1_done` | `done` | Drop numeric prefix |
| `1_canceled` | `canceled` | Drop numeric prefix |

**Constants update**:
```python
CLOSED_STATES = {
    "done": "Done",
    "canceled": "Canceled",
}
```

**Migration**: `UPDATE project_task SET state = CASE ... END`

#### Phase 4B: Rename tracking timestamp

| Current | Proposed | Rationale |
|---------|----------|-----------|
| `date_last_stage_update` | `date_last_status_change` | This field tracks BOTH step changes and state changes. "Status change" is the PMI-correct umbrella term. |

#### Phase 4C: Rename `auto_validation_state` on workflow step

| Current | Proposed | Rationale |
|---------|----------|-----------|
| `auto_validation_state` (string: "Automatic Kanban Status") | `auto_update_state` (string: "Auto-update State on Rating") | Describes what it does. No more "Kanban Status" ghost. |

---

## 5. Dependencies (Currently: `depend_on_ids` / `dependent_ids`)

### Problem

PMI calls these **Logical Relationships** with specific terms:
- **Predecessor**: activity that must finish before this one starts (Finish-to-Start)
- **Successor**: activity that waits on the predecessor

Odoo uses `depend_on_ids` ("Blocked By") and `dependent_ids` ("Blocking"),
which are functional but non-standard.

### Plan

| Current | Proposed | PMI Term |
|---------|----------|----------|
| `depend_on_ids` (string: "Blocked By") | `predecessor_ids` (string: "Predecessors") | Predecessor |
| `dependent_ids` (string: "Blocking") | `successor_ids` (string: "Successors") | Successor |
| `depend_on_count` | `predecessor_count` | — |
| `closed_depend_on_count` | `closed_predecessor_count` | — |
| `dependent_count` | `successor_count` | — |
| `allow_task_dependencies` | `allow_dependencies` | Shorter, same meaning |
| `is_blocked_by_dependences` (method) | `is_blocked_by_predecessors` | Clearer + fixes typo ("dependences") |
| relation table: `task_dependencies_rel` | `project_task_dependency_rel` | Follows Odoo naming convention |

**Note**: Odoo only implements Finish-to-Start (FS) dependencies. All four PMI
types (FS, FF, SS, SF) are not needed for now, but the naming should not
preclude future extension.

---

## 6. Priority (Currently: 0/1/2/3)

### Problem

PMI favors ordinal ranking over categorical buckets. The current labels
("Low priority", "Medium priority", "High priority", "Urgent") mix adjective
styles. The values are opaque numbers.

### Plan

| Current Value | Current Label | Proposed Label | Rationale |
|---------------|--------------|----------------|-----------|
| `"0"` | "Low priority" | "Normal" | Default should be neutral, not "low" |
| `"1"` | "Medium priority" | "Important" | Clearer than "medium" |
| `"2"` | "High priority" | "High" | Consistent |
| `"3"` | "Urgent" | "Urgent" | Already good |

Labels only — no value changes needed. Pure UI improvement.

---

## 7. Project Phases (Currently: `project.project.stage`)

### Problem

The model `project.project.stage` tracks the project's lifecycle (e.g.,
"Planning → Execution → Closing"). PMI calls these **phases**. The model name
uses "stage" which conflicts with task stages.

### Plan

| Current (retained) | New Canonical | Rationale |
|--------------------|--------------|-----------|
| `project.project.stage` (kept as-is) | `project.phase` (new model, new table) | PMI term. Old model stays for compatibility. |
| `project.project.stage_id` (kept as alias) | `project.project.phase_id` (new canonical field) | All new logic uses `phase_id` |
| Table: `project_project_stage` (kept) | `project_phase` (new table, data copied) | Old table untouched |

---

## 8. Documentation Cleanup

### Phase 8A: Delete outdated documentation

- **Delete** `core/addons/project/doc/stage_status.rst` — written for Odoo 8.0,
  references removed fields (`kanban_state`), claims `state` was removed (it's back).
  Replace with new doc.

### Phase 8B: Write new terminology reference

Create `core/addons/project/doc/terminology.rst`:

```rst
Project Module Terminology
==========================

This module follows PMI/PMBOK terminology where applicable.

Workflow Step (``project.workflow.step``)
    A named position in a project's Kanban board. Tasks move through
    workflow steps as work progresses (e.g., "Backlog → Development →
    Review → Done"). Each project defines its own set of steps.

    Displayed as: Kanban columns, statusbar in form view.

Task State (``project.task.state``)
    The internal condition of a task. Fixed set of values:

    - **In Progress** — actively being worked on
    - **Changes Requested** — reviewer requested modifications
    - **Approved** — validated, ready to proceed
    - **Blocked** — cannot proceed due to unfinished predecessors
    - **Done** — completed
    - **Canceled** — abandoned

    State is partially auto-computed: tasks with open predecessors are
    automatically set to "Blocked". Closed states (Done, Canceled) are
    never overridden by computation.

Personal Triage (``project.triage``)
    A user's personal time-horizon categorization for tasks they are
    assigned to. Not visible to other users. Not part of the project
    workflow. Default buckets: Inbox, Today, This Week, This Month,
    Later, Done, Cancelled.

    Displayed as: Kanban columns in "My Tasks" view only.

Project Phase (``project.phase``)
    The lifecycle stage of a project itself (not its tasks). Examples:
    "Planning", "Execution", "Closing". A project has exactly one
    current phase.

Milestone (``project.milestone``)
    A significant point or event in a project with zero duration.
    Milestones have a deadline and a reached/not-reached status.

Predecessor / Successor
    A dependency between two tasks. Task B has Task A as a predecessor
    if B cannot start until A is done (Finish-to-Start relationship).
    Task A is then a successor of nothing — Task B is A's successor.

Project Status (``project.update.status``)
    A health indicator for the project as a whole: On Track, At Risk,
    Off Track, On Hold, Complete. Updated via project updates.

Priority
    Relative urgency of a task: Normal (default), Important, High, Urgent.
```

---

## 9. CSS/JS Cleanup

### Dead CSS selectors
- `project_task_form_view.scss` lines 2, 7 reference `.o_kanban_state` — dead
  selectors from removed `kanban_state` field. **Delete**.

### Widget renames
| Current Widget | Proposed Widget | Location |
|---------------|----------------|----------|
| `project_task_state_selection` | `project_task_state_selection` | Keep (still shows state) |
| `task_stage_with_state_selection` | `task_step_with_state_selection` | Rename to match field |
| `rotting_statusbar_duration` | Keep | Generic enough |
| `badge_rotting` | Keep | Generic enough |

---

## 10. Implementation Phases

### Phase 1: New Models (Additive — no breakage)
**Risk**: LOW — purely additive, nothing removed or renamed yet
**Scope**: Create new canonical models alongside existing ones

1. Create `project.workflow.step` model (fields from `project.task.type` minus `user_id`)
2. Create `project.triage` model (personal bucket fields: `name`, `sequence`, `fold`, `user_id`)
3. Create `project.task.triage` junction model (same structure as `project.task.stage.personal`)
4. Create `project.phase` model (same structure as `project.project.stage`)
5. Write data migration: copy existing records into new tables
   - `project_task_type` WHERE `user_id IS NULL` → `project_workflow_step`
   - `project_task_type` WHERE `user_id IS NOT NULL` → `project_triage`
   - `project_project_stage` → `project_phase`
   - `project_task_user_rel` → `project_task_triage`
6. Add security rules for new models (`ir.model.access.csv`)

**Old models untouched**: `project.task.type`, `project.task.stage.personal`,
`project.project.stage` remain exactly as they are.

### Phase 2: New Fields on Existing Models (Additive)
**Risk**: LOW-MEDIUM — new fields added, old fields still work

1. Add `step_id` (M2O → `project.workflow.step`) on `project.task`
2. Add `triage_id` / `triage_ids` / `personal_triage_id` on `project.task`
3. Add `phase_id` on `project.project`
4. Add `workflow_step_ids` on `project.project`
5. Add `predecessor_ids` / `successor_ids` on `project.task` (new M2M using new relation table)
6. Add `date_last_status_change` on `project.task`
7. Add `predecessor_count`, `successor_count`, `closed_predecessor_count`
8. Write data migration: populate new fields from old fields
   - `step_id` ← mapping from `stage_id` via `project.task.type` → `project.workflow.step`
   - `predecessor_ids` ← copy from `depend_on_ids` relation table
   - `date_last_status_change` ← copy from `date_last_stage_update`
9. All old fields (`stage_id`, `personal_stage_type_id`, `depend_on_ids`, etc.) remain functional

### Phase 3: Migrate Logic to New Fields
**Risk**: MEDIUM — compute methods, constraints, business logic change targets
**Scope**: All project module logic switches from old fields to new fields

1. Rewrite `_compute_stage_id` → `_compute_step_id` (references `project.workflow.step`)
2. Rewrite `_compute_personal_stage_id` → `_compute_personal_triage_id`
3. Rewrite `_compute_state` to depend on `step_id` + `predecessor_ids.state`
4. Rewrite `is_blocked_by_dependences` → `is_blocked_by_predecessors`
5. Update `write()` method to use `step_id`, `predecessor_ids`, `date_last_status_change`
6. Update `CLOSED_STATES` and state selection values (drop prefixes, `waiting_normal` → `blocked`)
7. Rename `auto_validation_state` → `auto_update_state` on `project.workflow.step`
8. Turn old fields into computed aliases that delegate to new canonical fields:
   - `stage_id` → reads/writes via `step_id` mapping
   - `depend_on_ids` → reads/writes via `predecessor_ids`
   - `date_last_stage_update` → reads from `date_last_status_change`
9. Mark old fields/models with deprecation warnings in logs

### Phase 4: Views & UI
**Risk**: MEDIUM — XML changes, widget updates

1. Update all form/kanban/list/calendar views in `project` module to use new field names
2. Update search filters and group-by options
3. Update JS widgets (rename `task_stage_with_state_selection` → `task_step_with_state_selection`)
4. Remove dead CSS selectors (`.o_kanban_state` references)
5. Update `project_todo` views (switch from `personal_stage_type_id` to `triage_id`)
6. Update priority labels ("Low priority" → "Normal", "Medium priority" → "Important")

### Phase 5: Dependent Modules
**Risk**: HIGH — blast radius across 23+ modules
**Note**: Old aliases ensure nothing breaks immediately. This phase migrates
dependent code to use new names proactively.

1. Update `project_sms` (switch to `step_id`, `project.workflow.step`)
2. Update `sale_project` (inherit new model instead of `project.task.type`)
3. Update `project_enterprise` (switch state value references)
4. Update `industry_fsm` (switch to `step_id`, fold logic)
5. Update `hr_timesheet`, `sale_timesheet`, `timesheet_grid`
6. Update all other inheriting modules (mostly s/stage_id/step_id/ in views)
7. Update reports (`project_report.py`) to reference new fields
8. Update security rules for modules extending project

### Phase 6: Documentation & Tests
1. Delete `stage_status.rst`, write `terminology.rst`
2. Update all test files to use new field names and state values
3. Update test data (demo data, sample data XML)
4. Run full test suite for project + all dependent modules

---

## 11. Naming Convention Summary

### Models

| Old Model (RETAINED) | New Canonical Model | New Table | Status |
|----------------------|--------------------|-----------| -------|
| `project.task.type` | `project.workflow.step` (shared) | `project_workflow_step` | Old kept, new is source of truth |
| `project.task.type` | `project.triage` (personal) | `project_triage` | Old kept, new is source of truth |
| `project.task.stage.personal` | `project.task.triage` | `project_task_triage` | Old kept, new is source of truth |
| `project.project.stage` | `project.phase` | `project_phase` | Old kept, new is source of truth |
| `project.task` | `project.task` (no change) | — | Fields added, old fields become aliases |
| `project.milestone` | `project.milestone` (no change) | — | No changes needed |
| `project.update` | `project.update` (no change) | — | No changes needed |

### Fields on `project.task`

| Old Field (RETAINED as alias) | New Canonical Field | Type | Notes |
|-------------------------------|--------------------|----- |-------|
| `stage_id` | `step_id` | Many2one → `project.workflow.step` | Old becomes computed wrapper |
| `stage_id_color` | `step_color` | Integer (related) | Old becomes computed wrapper |
| `state` | `state` (same name) | Selection | Values cleaned (drop prefixes) |
| `personal_stage_type_ids` | `triage_ids` | Many2many → `project.triage` | Old becomes computed wrapper |
| `personal_stage_id` | `personal_triage_id` | Many2one → `project.task.triage` | Old becomes computed wrapper |
| `personal_stage_type_id` | `triage_id` | Many2one (related) | Old becomes computed wrapper |
| `date_last_stage_update` | `date_last_status_change` | Datetime | Old becomes computed wrapper |
| `depend_on_ids` | `predecessor_ids` | Many2many → `project.task` | Old becomes computed wrapper |
| `dependent_ids` | `successor_ids` | Many2many → `project.task` | Old becomes computed wrapper |
| `depend_on_count` | `predecessor_count` | Integer | Old becomes computed wrapper |
| `closed_depend_on_count` | `closed_predecessor_count` | Integer | Old becomes computed wrapper |
| `dependent_count` | `successor_count` | Integer | Old becomes computed wrapper |
| `allow_task_dependencies` | `allow_dependencies` | Boolean (related) | Old becomes computed wrapper |
| — | `milestone_id` (no change) | Many2one | Already correct |
| — | `priority` (no change) | Selection | Labels updated only |

### Fields on `project.workflow.step` (ex `project.task.type`)

| Current Field | Proposed Field | Notes |
|--------------|---------------|-------|
| `name` | `name` | No change |
| `sequence` | `sequence` | No change |
| `fold` | `fold` | No change |
| `color` | `color` | No change |
| `project_ids` | `project_ids` | No change |
| `auto_validation_state` | `auto_update_state` | Rename + new string |
| `mail_template_id` | `mail_template_id` | No change |
| `rating_template_id` | `rating_template_id` | No change |
| `rotting_threshold_days` | `rotting_threshold_days` | No change |
| `user_id` | REMOVED | Moved to `project.triage` |

### Fields on `project.project`

| Current Field | Proposed Field | Type |
|--------------|---------------|------|
| `stage_id` | `phase_id` | Many2one → `project.phase` |
| `stage_id_color` | `phase_color` | Integer (related) |
| `type_ids` | `workflow_step_ids` | Many2many → `project.workflow.step` |

### State Values on `project.task`

| Current | Proposed | String |
|---------|----------|--------|
| `01_in_progress` | `in_progress` | "In Progress" |
| `02_changes_requested` | `changes_requested` | "Changes Requested" |
| `03_approved` | `approved` | "Approved" |
| `04_waiting_normal` | `blocked` | "Blocked" |
| `1_done` | `done` | "Done" |
| `1_canceled` | `canceled` | "Canceled" |

### Methods

| Current Method | Proposed Method | Notes |
|---------------|----------------|-------|
| `_compute_stage_id` | `_compute_step_id` | |
| `_read_group_stage_ids` | `_read_group_step_ids` | |
| `_compute_personal_stage_id` | `_compute_personal_triage_id` | |
| `_search_personal_stage_id` | `_search_personal_triage_id` | |
| `_get_default_personal_stage_create_vals` | `_get_default_triage_vals` | Shorter |
| `_populate_missing_personal_stages` | `_populate_missing_triages` | |
| `_read_group_personal_stage_type_ids` | `_read_group_triage_ids` | |
| `is_blocked_by_dependences` | `is_blocked_by_predecessors` | Fix typo + PMI term |

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking dependent modules | LOW | HIGH | Additive approach: old models/fields retained as aliases. Nothing removed. |
| Data migration errors (new tables) | MEDIUM | MEDIUM | New tables are populated from old data; old tables untouched. Reversible. |
| State value migration | MEDIUM | HIGH | `UPDATE` on `project_task.state` is atomic. Test on DB copy first. |
| JS widget breakage | MEDIUM | MEDIUM | Comprehensive widget testing. Old widget names can coexist. |
| Dual-model sync drift | MEDIUM | MEDIUM | Write hooks on old models proxy to new ones. Test both paths. |
| Report breakage | LOW | LOW | Reports migrated in Phase 5; old field aliases still work as fallback. |
| Missing rename in obscure location | MEDIUM | LOW | grep-based audit before each phase. Aliases provide safety net. |

---

## 13. Success Criteria

### v19.0 (this release)
- [ ] New canonical models exist: `project.workflow.step`, `project.triage`, `project.task.triage`, `project.phase`
- [ ] New canonical fields exist on `project.task` and `project.project`
- [ ] All project module logic references new models/fields (not old ones)
- [ ] Old models (`project.task.type`, `project.task.stage.personal`, `project.project.stage`) still exist and function
- [ ] Old fields (`stage_id`, `personal_stage_type_id`, `depend_on_ids`, etc.) still exist as computed aliases
- [ ] State values cleaned (no numeric prefixes, no `_normal` suffix)
- [ ] Dependency fields use PMI "predecessor/successor" terminology
- [ ] `stage_status.rst` replaced with `terminology.rst`
- [ ] All 23+ dependent modules updated to reference new fields and passing tests
- [ ] Data migration script populates new tables from old tables
- [ ] Dead CSS selectors removed
- [ ] Priority labels updated (Low → Normal)

### v20.0 (future — when ready)
- [ ] Old models dropped
- [ ] Old field aliases removed
- [ ] Old database tables dropped
- [ ] Old relation tables dropped
