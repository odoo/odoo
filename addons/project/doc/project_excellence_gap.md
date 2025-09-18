# Implementation Plan: Project Module Excellence

## Context

The investigation at `core/addons/project/doc/pm_excellence_investigation.md` identified
17 evidence-backed gaps between PM best practices and Odoo's project module. This plan
addresses all gaps across 4 phases, implemented directly in `core/addons/project/` per
the fork philosophy ("we own the codebase").

**Key architectural insight from exploration**: The project module already tracks stage
transition timestamps (`date_last_stage_update`, `mail.tracking.duration.mixin`,
`duration_tracking` JSON field) and has a status update model (`project.update` with
`on_track`/`at_risk`/`off_track`/`on_hold` states). Many "new" features are extensions
of existing infrastructure, not greenfield development.

---

## Phase 1: Flow and Visibility

### 1.1 Flow Metrics on Tasks and Projects

**Rationale**: Strongest evidence (Little's Law [T1] + DORA [T1-2]). Data already
partially exists in stage transition timestamps.

**New computed fields on `project.task`** (`models/project_task.py`):

```
cycle_time_hours    Float   Computed, stored. Hours from entering first active stage
                            to entering a closed state. Uses resource calendar for
                            working hours (existing pattern: working_hours_close).
                            NULL until task is closed.

lead_time_hours     Float   Computed, stored. Hours from create_date to date_end
                            (task closure). Uses resource calendar. NULL until closed.

time_in_stage_hours Float   Computed. Working hours since date_last_stage_update.
                            Live metric — shows how long current stage has lasted.

is_stale            Boolean Computed, search-enabled. True when time_in_stage exceeds
                            the stage's rotting_threshold_days (field already exists
                            on project.task.type).
```

**New computed fields on `project.project`** (`models/project_project.py`):

```
avg_cycle_time      Float   Computed, stored. Average cycle_time_hours of closed tasks
                            in last 90 days. Recalculated on task closure.

median_cycle_time   Float   Computed. Median of cycle_time_hours for recent closed tasks.

throughput_week     Float   Computed, stored. Tasks closed per week (rolling 4-week avg).

wip_count           Integer Computed. Count of tasks in open, non-waiting states.

lead_time_p85       Float   Computed. 85th percentile lead time for closed tasks
                            (last 90 days). Answers "when will this likely be done?"
```

**WIP limits on stages** — extend `project.task.type` (`models/project_task_type.py`):

```
wip_limit           Integer Default 0 (unlimited). Maximum tasks allowed in this stage
                            per project. 0 = no limit.

wip_limit_warning   Boolean Computed on project.task.type per project context.
                            True when current WIP >= wip_limit.
```

**New report model** — `project.flow.report` (`report/project_flow_report.py`):
SQL-based report model (following the pattern of `project.task.burndown.chart.report`)
providing:
- Cumulative Flow Diagram data (task count per stage per date)
- Cycle time scatter plot data (task completion date vs. cycle time)
- Throughput histogram data (tasks completed per period)
- Lead time distribution data

**New views** (`views/project_flow_views.xml` + `static/src/views/flow_metrics/`):
- **CFD view**: Stacked area chart (extend graph view or custom JS like burndown_chart)
- **Cycle time scatter plot**: Custom JS graph component
- **Throughput chart**: Bar chart showing tasks/week over time
- **Flow metrics dashboard widget**: Add to `ProjectRightSidePanel` component showing
  avg cycle time, throughput, WIP count, lead time P85

**Files to modify:**
- `models/project_task.py` — Add cycle_time, lead_time, time_in_stage, is_stale fields
- `models/project_project.py` — Add avg_cycle_time, throughput, wip_count, lead_time_p85
- `models/project_task_type.py` — Add wip_limit field
- `views/project_task_views.xml` — Add flow metrics to task form (read-only section)
- `views/project_project_views.xml` — Add flow summary to project form
- `static/src/components/project_right_side_panel/` — Add flow metrics section
- `report/project_flow_report.py` — New SQL report model
- `views/project_flow_views.xml` — New view definitions (CFD, scatter, throughput)
- `security/ir.model.access.csv` — Access rules for new report model

**Critical files to read first:**
- `report/project_task_burndown_chart_report.py` — Pattern for SQL time-series reports
- `models/project_task.py:working_hours_close` — Pattern for resource-calendar-aware duration
- `static/src/views/burndown_chart/` — Pattern for custom graph JS components

---

### 1.2 Risk Register

**Rationale**: Consistent CSF in meta-analyses [T2]. Simple data model, high value.

**New model** — `project.risk` (`models/project_risk.py`):

```
name                Char        Required. Risk title.
description         Html        Detailed risk description.
project_id          Many2one    project.project, required, ondelete=cascade, indexed.
task_id             Many2one    project.task, optional. Link risk to specific task.
category            Selection   technical, organizational, external, financial, schedule.
probability         Selection   1 (Rare) through 5 (Almost Certain).
impact              Selection   1 (Negligible) through 5 (Catastrophic).
risk_score          Integer     Computed: probability * impact. Stored, indexed.
risk_level          Selection   Computed from risk_score: low (1-4), medium (5-9),
                                high (10-15), critical (16-25).
response_strategy   Selection   mitigate, transfer, accept, avoid, exploit.
response_plan       Html        Concrete response actions.
owner_id            Many2one    res.users. Person responsible for monitoring/response.
state               Selection   identified, assessed, mitigated, resolved, accepted.
date_identified     Date        Default today.
date_resolved       Date        Set when state = resolved.
active              Boolean     Default True. Archive resolved risks.
```

**Extensions to existing models:**

```
project.project:
    risk_ids            One2many    project.risk
    risk_count          Integer     Computed. Total active risks.
    risk_score_total    Integer     Computed. Sum of active risk scores.
    high_risk_count     Integer     Computed. Risks with risk_level in (high, critical).

project.task:
    risk_ids            One2many    project.risk (via task_id)
    risk_count          Integer     Computed.
```

**Views:**
- Risk register list view (grouped by risk_level, colored by severity)
- Risk form view (description, assessment, response plan, owner)
- Risk matrix visualization (pivot: probability rows x impact columns, count measure)
- Smart button on project form showing risk count (colored red if high_risk_count > 0)
- Smart button on task form showing associated risks

**Files to create:**
- `models/project_risk.py` — New model
- `views/project_risk_views.xml` — List, form, search, matrix views
- `security/ir.model.access.csv` — Add access rules

**Files to modify:**
- `models/__init__.py` — Import project_risk
- `models/project_project.py` — Add risk_ids, risk_count, risk_score_total
- `models/project_task.py` — Add risk_ids, risk_count
- `views/project_project_views.xml` — Add risk smart button
- `views/project_task_views.xml` — Add risk smart button
- `views/project_menus.xml` — Add Risk Register menu under project

---

### 1.3 Automated Health Indicators

**Rationale**: Prevents status theater (green-green-green-RED) [T2-3]. Extends
existing `project.update` model which already has on_track/at_risk/off_track states.

**New computed fields on `project.project`** (`models/project_project.py`):

```
health_score        Integer     Computed, stored. 0-100 composite score based on:
                                - Schedule health (% tasks on time vs overdue)
                                - Milestone health (% milestones on track)
                                - Risk health (inverse of normalized risk_score_total)
                                - Workload health (team utilization balance)
                                - Staleness health (% of tasks not stale)

health_status       Selection   Computed from health_score:
                                healthy (80-100), attention (60-79),
                                warning (40-59), critical (0-39).

health_trend        Selection   Computed. improving, stable, degrading.
                                Based on health_score delta over last 2 weeks.

schedule_deviation  Float       Computed. % of tasks past deadline without closure.

is_stale_project    Boolean     Computed. True if no task activity in 14+ days.

health_override     Selection   Optional manual override (same values as health_status).
health_override_reason Html     Required when health_override is set. Explanation.
```

**Extend `project.update`** (`models/project_update.py`):
- Add `computed_status` field that shows the automated health_status
- When creating an update, pre-fill status from computed health if no override exists
- Show delta between manual status and computed status as a warning

**Views:**
- Health indicator badge on project kanban cards (color-coded dot)
- Health details section on project form (expandable showing component scores)
- Health trend sparkline on project list view
- Warning banner when manual override differs from computed health by 2+ levels

**Files to modify:**
- `models/project_project.py` — Add health computation fields
- `models/project_update.py` — Add computed_status, pre-fill logic
- `views/project_project_views.xml` — Add health badges and details
- `static/src/views/project_project_kanban/` — Add health indicator to kanban cards

---

### 1.4 Cross-Project Resource Visibility

**Rationale**: Overcommitment is the #1 portfolio-level failure [T2].

**New report model** — `project.resource.report` (`report/project_resource_report.py`):
SQL view aggregating per employee across all active projects:

```
user_id             Many2one    res.users
project_id          Many2one    project.project
allocated_hours     Float       Sum of allocated_hours on assigned open tasks
task_count          Integer     Count of assigned open tasks
project_count       Integer     Count of distinct projects
utilization_pct     Float       Computed: allocated_hours / available_hours * 100
is_overallocated    Boolean     Computed: utilization_pct > 100
```

**Views:**
- Pivot view: Users (rows) x Projects (columns), allocated_hours measure
- Graph view: Bar chart of utilization_pct per user, red line at 100%
- List view with overallocation highlighting

**Menu**: Add under Project > Reporting > Resource Utilization

**Files to create:**
- `report/project_resource_report.py` — SQL report model
- `report/project_resource_report_views.xml` — Pivot, graph, list views

**Files to modify:**
- `report/__init__.py` — Import
- `views/project_menus.xml` — Add menu entry
- `security/ir.model.access.csv` — Access rules

---

### 1.5 Retrospective and Action Tracking

**Rationale**: Knowledge management research [T2-3]. Low effort, high cultural impact.

**New models** (`models/project_retrospective.py`):

```
project.retrospective:
    name                Char        Required. Title (e.g., "Sprint 5 Retro", "Q1 Review").
    project_id          Many2one    project.project, required, indexed.
    date                Date        Required. Default today.
    facilitator_id      Many2one    res.users.
    went_well           Html        What went well.
    to_improve          Html        What needs improvement.
    action_ids          One2many    project.retrospective.action.
    action_count        Integer     Computed.
    open_action_count   Integer     Computed. Actions not yet completed.
    previous_id         Many2one    project.retrospective. Link to previous retro.
    carried_action_ids  Computed    Actions from previous_id still open.
    state               Selection   draft, done.

project.retrospective.action:
    name                Char        Required. Action description.
    retrospective_id    Many2one    project.retrospective, required.
    project_id          Related     Via retrospective_id.project_id.
    owner_id            Many2one    res.users, required.
    due_date            Date
    state               Selection   open, in_progress, done, dropped.
    resolution_note     Text        How was this resolved?
    carried_from_id     Many2one    Self. If carried from a previous retro's action.
    category            Selection   estimation, scope, communication, technical,
                                    process, team, tooling.
```

**Extensions:**
```
project.project:
    retrospective_ids       One2many    project.retrospective
    retrospective_count     Integer     Computed
    open_retro_actions      Integer     Computed. Outstanding actions across all retros.
```

**Views:**
- Retrospective form: went_well / to_improve / actions (inline one2many)
- Retrospective list: date, facilitator, action count, open actions (highlighted if > 0)
- Action list: filtered to open actions, grouped by category
- Smart button on project form: "Retros (N)" with badge for open actions
- When creating new retro: auto-populate carried_action_ids from previous retro

**Files to create:**
- `models/project_retrospective.py`
- `views/project_retrospective_views.xml`

**Files to modify:**
- `models/__init__.py`, `models/project_project.py`, `views/project_menus.xml`,
  `security/ir.model.access.csv`

---

## Phase 2: Governance and Measurement

### 2.1 Portfolio Dashboard

**New action/view**: All-projects dashboard with:
- Kanban grouped by health_status (healthy/attention/warning/critical)
- List view with: project name, health badge, progress %, avg cycle time, throughput,
  risk score, resource utilization %, strategic alignment tag
- Pivot: projects x key metrics
- Graph: portfolio health distribution over time

**Files to create:**
- `views/project_portfolio_views.xml` — Dashboard views
- `static/src/views/project_portfolio/` — Custom JS dashboard (optional)

**Files to modify:**
- `views/project_menus.xml` — Add Portfolio menu entry

---

### 2.2 Benefits Realization Tracking

**New model** — `project.benefit` (`models/project_benefit.py`):

```
project.benefit:
    name                Char        Required. Expected benefit.
    project_id          Many2one    project.project, required.
    description         Html        How this benefit will be realized.
    measurement_method  Text        How to measure (specific, quantified).
    target_value        Float       Quantified target.
    target_unit         Char        Unit of measurement.
    actual_value        Float       Measured actual (updated post-delivery).
    achievement_pct     Float       Computed: actual / target * 100.
    accountable_id      Many2one    res.users. Business owner.
    review_date_1       Date        3-month review.
    review_date_2       Date        6-month review.
    review_date_3       Date        12-month review.
    state               Selection   expected, tracking, achieved, partially, not_achieved.
    notes               Html        Review notes.
```

**Extensions on project.project:**
```
    benefit_ids             One2many
    benefit_count           Integer     Computed
    benefit_achievement_avg Float       Computed. Avg achievement_pct.
```

**Views:** Form with measurement fields, list with achievement progress bars, smart
button on project.

---

### 2.3 Project Baseline (Snapshot)

**New model** — `project.baseline` (`models/project_baseline.py`):

```
project.baseline:
    name                Char        Required. "Original Plan", "Replan v2", etc.
    project_id          Many2one    project.project, required.
    date_created        Datetime    Default now.
    created_by_id       Many2one    res.users.
    is_current          Boolean     Only one per project.
    line_ids            One2many    project.baseline.line.

project.baseline.line:
    baseline_id         Many2one    project.baseline, required.
    task_id             Many2one    project.task.
    task_name           Char        Snapshot of task name.
    planned_start       Date        Snapshot of date_assign or planned start.
    planned_end         Date        Snapshot of date_deadline.
    planned_hours       Float       Snapshot of allocated_hours.
    milestone_id        Many2one    Snapshot of milestone_id.
```

**Usage**: Create baseline at project kickoff. Compare actual progress against baseline
in Gantt view (dual bars: baseline vs. actual). Compute schedule variance per task.

**Extensions on project.project:**
```
    baseline_ids            One2many
    current_baseline_id     Many2one    Computed (is_current=True).
    schedule_variance       Float       Computed. Avg days ahead/behind baseline.
```

---

### 2.4 Historical Estimation Data

**New model** — `project.history` (`models/project_history.py`):
Auto-created when a project reaches "done" stage:

```
project.history:
    project_id          Many2one    project.project, required.
    date_completed      Date
    planned_duration    Integer     Days from date_start to planned date_end.
    actual_duration     Integer     Days from date_start to actual completion.
    duration_variance   Float       Computed: (actual - planned) / planned * 100.
    planned_hours       Float       Sum of allocated_hours.
    actual_hours        Float       Sum of effective_hours.
    hours_variance      Float       Computed: (actual - planned) / planned * 100.
    task_count          Integer     Total tasks.
    team_size           Integer     Distinct assignees.
    tag_ids             Many2many   Copied from project tags (for reference class search).
    complexity_score    Integer     Computed heuristic (task count * dependency density).
```

**Reference class query**: Action on project form "Find Similar Projects" that searches
project.history by tag similarity and team size range, showing actual durations.

---

### 2.5 Gate Review / Kill Criteria

**New model** — `project.gate` (`models/project_gate.py`):

```
project.gate:
    name                Char        Required. "Feasibility Gate", "Go-Live Gate".
    project_id          Many2one    project.project, required.
    sequence            Integer     Gate order.
    milestone_id        Many2one    project.milestone. Trigger at milestone.
    criteria_ids        One2many    project.gate.criterion.
    state               Selection   pending, passed, failed, deferred.
    review_date         Date
    reviewer_ids        Many2many   res.users.
    decision_notes      Html
    kill_criteria       Html        Pre-defined conditions for project cancellation.

project.gate.criterion:
    gate_id             Many2one    project.gate, required.
    name                Char        Required. What is being evaluated.
    met                 Boolean     Was the criterion met?
    evidence            Text        Supporting evidence.
```

---

### 2.6 Pre-Mortem Template

**Extension to project.project** — Add a structured pre-mortem step:

```
project.project:
    premortem_done          Boolean     Was pre-mortem conducted?
    premortem_date          Date
    premortem_participants  Many2many   res.users.
    premortem_notes         Html        "Imagine this project has failed. Why?"
```

Simple addition — the value is in making pre-mortem a standard initiation step.
Add to project form as a collapsible section in a "Risk & Planning" tab.

---

## Phase 3: Advanced Scheduling

### 3.1 Additional Dependency Types

**Extend dependency model** — Currently `task_dependencies_rel` (Many2many) only
supports finish-to-start.

**New model** — `project.task.dependency` (replaces Many2many with proper model):

```
project.task.dependency:
    task_id             Many2one    project.task (the dependent task).
    depends_on_id       Many2one    project.task (the predecessor).
    dependency_type     Selection   fs (finish-to-start), ss (start-to-start),
                                    ff (finish-to-finish), sf (start-to-finish).
                                    Default: fs.
    lag_hours           Float       Default 0. Positive = lag, negative = lead.
```

**Migration**: Convert existing `task_dependencies_rel` records to `project.task.dependency`
with `dependency_type='fs'` and `lag_hours=0`.

**Impact**: Requires updating `_compute_state()` to handle all four dependency types.
Gantt view rendering needs to show different line styles per type.

---

### 3.2 Critical Path Calculation

**New method on project.project**: `_compute_critical_path()`

Algorithm: Forward pass (earliest start/finish) + backward pass (latest start/finish)
through the dependency network. Tasks with zero float = critical path.

**New fields on project.task:**
```
    earliest_start      Date    Computed from dependency network.
    latest_start        Date    Computed from dependency network.
    total_float         Float   Computed: latest_start - earliest_start (in days).
    is_critical_path    Boolean Computed: total_float == 0.
```

**Views**: Gantt view highlighting of critical-path tasks (red border or distinct color).
Filter in task list/search for critical-path tasks.

**Note**: This is the most algorithmically complex feature. The critical path must be
recomputed when tasks are added/removed, dependencies change, or dates change.
Consider caching and lazy recomputation (only on explicit request or Gantt view load).

---

### 3.3 Resource Leveling

**Deferred**: Marked as "Very High" effort in the investigation. This requires a
constraint-satisfaction solver or heuristic scheduler. Should be designed as a
separate phase after dependency types and critical path are stable.

**Minimal approach**: Warning system (not automatic leveling). When an employee's
allocated hours across concurrent tasks exceed available hours, show a warning on
the task form and in the resource utilization report. Let humans resolve conflicts.

---

## Phase 4: Agile Extensions (Optional)

### 4.1 Sprint Management

**New models** (`models/project_sprint.py`):

```
project.sprint:
    name                Char        Required. "Sprint 12", "March Iteration".
    project_id          Many2one    project.project, required.
    date_start          Date        Required.
    date_end            Date        Required.
    goal                Text        Sprint goal.
    state               Selection   planning, active, review, closed.
    capacity_hours      Float       Total team hours available.
    task_ids            Many2many   project.task. Tasks in this sprint.
    task_count          Integer     Computed.
    completed_count     Integer     Computed. Closed tasks.
    completion_pct      Float       Computed.
    velocity            Float       Computed. Effort completed (allocated_hours of done tasks).
    story_points        Float       Computed. Sum of story_points on done tasks. Optional.
```

**Extension on project.task:**
```
    sprint_id           Many2one    project.sprint.
    story_points        Float       Optional estimation field.
```

**Extension on project.project:**
```
    sprint_ids          One2many    project.sprint.
    active_sprint_id    Many2one    Computed (state=active).
    use_sprints         Boolean     Feature flag (like allow_milestones).
```

**Views:**
- Sprint planning board: Kanban of tasks draggable between backlog and sprint
- Sprint burndown: Filtered burndown chart for active sprint tasks
- Velocity chart: Bar chart of velocity per closed sprint

---

### 4.2 Monte Carlo Forecasting

**New transient model** — `project.forecast.wizard`:

Uses historical throughput data (from project.flow.report) to run Monte Carlo
simulation. Input: number of remaining items. Output: probabilistic completion dates
(50th, 85th, 95th percentile).

Display as a simple dialog with date predictions and confidence intervals.

---

## Verification Strategy

### Per-Feature Testing

Each new model and computed field needs:
1. **Unit tests** in `tests/` (following existing pattern: `test_project_flow.py`, etc.)
2. **Test data** via `demo/` XML files
3. **Access control** testing (manager vs. user vs. portal)

### Integration Testing

```bash
# Run project module tests
> ./odoo.log && ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
    --test-tags '/project' -u project --stop-after-init --workers=0

# Check results
grep "tests when loading" ./odoo.log
grep -E "ERROR.*FAIL:" ./odoo.log | tail -20
```

### Manual Verification

1. Create a project with 10+ tasks across 4 stages
2. Move tasks through stages over time
3. Verify flow metrics compute correctly (cycle time, throughput, WIP)
4. Create risks, verify risk matrix pivot view
5. Verify health indicators update automatically
6. Create retrospective with actions, verify carryover
7. Create baseline, modify schedule, verify variance computation

---

## Implementation Order (Within Each Phase)

### Phase 1 (recommended first implementation):
1. Flow metrics fields on task/project (foundation — no UI needed to validate)
2. WIP limits on stages (small model change)
3. Risk register model + views (independent, can be done in parallel)
4. Health indicators (depends on flow metrics being computed)
5. Flow metrics views/JS (depends on flow report model)
6. Resource utilization report (independent)
7. Retrospective model + views (independent)

### Phase 2:
1. Benefits realization model (independent)
2. Pre-mortem fields (trivial addition)
3. Project baseline model (independent)
4. Gate review model (depends on milestones working)
5. Historical estimation data (depends on project completion workflow)
6. Portfolio dashboard (depends on health indicators existing)

### Phase 3:
1. Dependency type model (replaces Many2many — migration needed)
2. Critical path algorithm (depends on new dependency model)
3. Resource leveling warnings (depends on resource report)

### Phase 4:
1. Sprint model (independent)
2. Sprint views and planning board
3. Monte Carlo wizard (depends on flow report historical data)

---

## File Summary

**New files to create:**
- `models/project_risk.py`
- `models/project_retrospective.py`
- `models/project_benefit.py`
- `models/project_baseline.py`
- `models/project_history.py`
- `models/project_gate.py`
- `models/project_sprint.py` (Phase 4)
- `models/project_task_dependency.py` (Phase 3)
- `report/project_flow_report.py`
- `report/project_resource_report.py`
- `views/project_risk_views.xml`
- `views/project_retrospective_views.xml`
- `views/project_flow_views.xml`
- `views/project_benefit_views.xml`
- `views/project_baseline_views.xml`
- `views/project_gate_views.xml`
- `views/project_portfolio_views.xml`
- `views/project_sprint_views.xml` (Phase 4)
- `report/project_flow_report_views.xml`
- `report/project_resource_report_views.xml`
- `static/src/views/flow_metrics/` (JS components for CFD, scatter plot)
- `static/src/components/project_health_indicator/` (health badge widget)
- `tests/test_project_flow.py`
- `tests/test_project_risk.py`
- `tests/test_project_retrospective.py`
- `tests/test_project_health.py`

**Existing files to modify:**
- `models/__init__.py` — Import new models
- `models/project_task.py` — Flow metric fields, risk_ids, sprint_id
- `models/project_project.py` — Health indicators, flow aggregates, feature flags
- `models/project_task_type.py` — wip_limit field
- `models/project_update.py` — computed_status from health indicators
- `views/project_project_views.xml` — Health badges, smart buttons, new tabs
- `views/project_task_views.xml` — Flow metrics display, risk button
- `views/project_menus.xml` — Risk Register, Retrospectives, Portfolio, Resource menus
- `security/ir.model.access.csv` — All new model access rules
- `__manifest__.py` — New data files, assets
- `static/src/components/project_right_side_panel/` — Flow metrics + risk sections
- `report/__init__.py` — Import new reports
