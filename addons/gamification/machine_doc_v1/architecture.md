# Gamification Architecture

## Subsystem Overview

The module has 8 interconnected subsystems:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           res.users (extended)                          │
│  karma ◄── karma.tracking    rank_id ◄── karma.rank    badge_ids       │
│  streak_ids   featured_badge_ids   xp_progress_percent   visibility    │
└──┬───────────────┬─────────────────────────┬─────────────────────┬─────┘
   │               │                         │                     │
┌──▼──────┐  ┌─────▼─────┐  ┌───────────────▼──────┐  ┌──────────▼─────┐
│CHALLENGE│  │RECOGNITION│  │    PROGRESSION        │  │   JOURNEYS     │
│& GOALS  │  │           │  │                       │  │                │
│         │  │ Badges    │  │ Karma    Skill Trees  │  │ Quests (steps) │
│Challenge│─▶│ Kudos     │─▶│ Ranks    Skill Nodes  │  │ Seasons        │
│Goal     │  │ Mentorship│  │ Streaks  Achievements │  │                │
│GoalDef  │  │           │  │                       │  │                │
└────┬────┘  └─────┬─────┘  └───────────┬───────────┘  └───────┬────────┘
     │             │                    │                       │
     └─────────────┴────────────────────┴───────────────────────┘
                              │
              ┌───────────────▼────────────────┐
              │        SOCIAL & ANALYTICS      │
              │                                │
              │  Activity Feed (unified)       │
              │  Engagement Snapshots (daily)  │
              │  Leaderboards (karma/season)   │
              │  Nudges (smart notifications)  │
              │  Adaptive Difficulty           │
              │  Teams                         │
              └────────────────────────────────┘
```

### Subsystem Details

**1. Challenges & Goals** — Manager-assigned objectives with periodic evaluation.
The challenge orchestrates goal creation and lifecycle for groups of users.
Supports adaptive difficulty based on user performance history.

**2. Recognition** — Peer-to-peer and system-to-user reward mechanisms.
Badges have complex granting rules. Kudos are lightweight, always-available.
Mentorship pairs experienced users with newcomers for guided progression.

**3. Progression** — XP-based advancement system.
Karma is the universal currency. Ranks are thresholds. Streaks reward consistency.
Achievements reward discovery. Skill trees provide branching progression paths.

**4. Journeys** — Multi-step narrative experiences.
Quests wrap goal definitions in ordered, prerequisite-linked steps with story.
Seasons create time-limited events with exclusive rewards and fresh leaderboards.

**5. Social & Analytics** — Visibility and measurement layer.
Activity feed aggregates all gamification events into a single stream.
Engagement snapshots capture daily metrics for trend analysis.
Smart nudges detect disengagement patterns and send targeted notifications.
Leaderboards respect privacy visibility settings.

---

## Karma Flow

Karma is the central currency. It flows from multiple sources:

```
                    ┌─────────────┐
Kudos ──────────────▶             │
                    │   _add_karma │
Streak daily ───────▶  _add_karma  │──▶ gamification.karma.tracking.create()
                    │   _batch    │         │
Achievement ────────▶             │         ▼
                    └─────────────┘    res.users._compute_karma()
                                           │
Manual / write() ──────────────────────────┘
                                           │
                                           ▼
                                    _recompute_rank()
                                           │
                                    ┌──────▼──────┐
                                    │ rank_changed │
                                    │ → badges     │
                                    │ → bus notif  │
                                    │ → email      │
                                    └─────────────┘
```

**Key invariant:** `res.users.karma` is the **sum of every recorded gain** —
`SUM(new_value - old_value)` over that user's `gamification.karma.tracking`
rows. Direct writes to the `karma` field trigger `_add_karma_batch` (via
`res.users.write()`) which creates a tracking record, which then triggers
`_compute_karma` via `@api.depends("karma_tracking_ids.new_value",
"karma_tracking_ids.old_value")`.

This replaces an earlier "latest row wins" rule
(`DISTINCT ON (user_id) ... ORDER BY tracking_date DESC, id DESC`), which
silently dropped karma in two reachable cases: a row inserted with an older
`tracking_date` never became the winner, and rows created together in one
`create()` batch all chained from the same pre-batch value so only the last
counted. Summing gains also matches what every other consumer of this table
already did (`_get_tracking_karma_gain_position`, the season leaderboard, the
engagement snapshots), so the whole module now shares one definition of karma.

**Caveat:** When karma is set via `write()`, the tracking record has no `source`
or `reason` metadata — it defaults to the current user and `_("Add Manually")`.
Always prefer `_add_karma(gain, source, reason)` for traceable karma changes.

**Consolidation is karma-neutral by construction:** the consolidated row's gain
equals the total gain of the rows it replaces, so collapsing a month cannot
change any user's karma. No `skip_karma_computation` escape hatch exists any
more — it was actively harmful, because Odoo clears a field's to-compute flag
*before* invoking the compute, so the old early-`return` consumed pending karma
recomputes instead of deferring them, and its `flush_all()` did so across the
entire transaction.

---

## Challenge Lifecycle

```
1. Manager creates challenge (draft)
   ├── Defines line_ids (goal definitions + targets)
   ├── Sets user_ids or user_domain
   └── Sets reward badges (per-user, top-3)

2. action_start() → write(state=inprogress)
   ├── _recompute_challenge_users()  (add users from domain)
   └── _generate_goals_from_challenge()
       └── Creates one gamification.goal per user × line

3. Daily cron: _cron_update() → _update_all()
   ├── Add new users matching user_domain
   ├── Generate missing goals
   ├── goal.update_goal() for each goal (filtered by recent user presence):
   │   ├── computation_mode=count → search_count(domain)
   │   ├── computation_mode=sum → _read_group(domain, field:sum)
   │   ├── computation_mode=python → safe_eval(compute_code)
   │   └── computation_mode=manually → _check_remind_delay()
   ├── State transitions (in goal._get_write_values):
   │   ├── current >= target → state = reached
   │   └── end_date passed → state = failed, closed = True
   ├── reward_realtime: grant badge immediately on goal reached
   ├── Send reports (if frequency matches)
   └── Close expired periods, generate new goals for next period

4. state = done
   └── Grant ranking rewards (1st/2nd/3rd badges)
```

---

## Streak Cron Pipeline

**Cron:** `ir_cron_update_streaks` — runs daily at 06:00

```
_cron_update_streaks()
    │
    ├── if today.day == 1:
    │       reset freeze_remaining for all active streaks
    │
    └── for each active streak where last_activity_date < today:
            │
            ├── streak_type._check_user_activity(user, yesterday)
            │       │
            │       ├── safe_eval(domain, {user, date_from, date_to})
            │       └── search_count(domain + date filters, limit=1)
            │
            ├── if activity found:
            │       streak._record_activity()
            │           ├── current_count += 1
            │           ├── longest_count = max(longest, current)
            │           ├── user._add_karma(bonus * milestone_multiplier)
            │           └── if milestone day: bus notification
            │
            ├── elif freeze_remaining > 0:
            │       freeze_remaining -= 1
            │
            └── else:
                    streak._break_streak()
                        ├── current_count = 0
                        └── state = broken

            (every branch ends with: last_checked_date = today)
```

**Idempotency:** the cron's re-entry guard is `last_checked_date`, not
`last_activity_date`. The latter only advances when activity is *found*, so
the freeze and break branches used to repeat: a second run on the same day
burned another freeze day and a third broke an intact streak. Each streak is
also processed inside its own savepoint, so one malformed `domain` cannot roll
back the whole run (and, since `_order` is stable, block the same streaks every
following night).

**Timezone:** a streak day is the *user's* calendar day. `_check_user_activity`
resolves `user.tz → company partner tz → UTC` (`_get_streak_tz_name`, mirroring
`hr.employee._get_tz`), builds the `[00:00, 23:59:59]` window in that zone, and
converts it to UTC for the query — so **storage and the query stay UTC**; only
the window boundaries are local. Users are bucketed by timezone so a batch
still issues one query per zone rather than one per user.

Do **not** substitute `fields.Date.context_today` here: it reads `env.tz`,
which in a cron is the *cron user's* timezone, not the streak owner's. This
follows the same convention as `lunch.supplier._compute_available_today`, which
answers a per-record calendar-day question in that record's zone from cron
code.

---

## Achievement Cron Pipeline

**Cron:** `ir_cron_check_achievements` — runs daily at 07:00

```
_cron_check_achievements()
    │
    └── for each active achievement:
            _check_achievement_for_users(all_internal_users)
                │
                ├── Filter out already-unlocked users
                │
                └── for each candidate:
                        safe_eval(trigger_domain, {user})
                        if search_count(domain) >= trigger_count:
                            create achievement.unlock
                            _grant_rewards()
                                ├── user._add_karma(karma_reward)
                                ├── badge.user.create + _send_badge()
                                └── bus notification
```

---

## Karma Consolidation

**Cron:** `ir_cron_consolidate` — runs monthly on 1st at 04:00

Purpose: Compress old tracking records into one record per user per month.
Processes records from the start of the month that is 2 calendar months
before the current month (e.g., on March 26 it processes January records).

```
_consolidate_cron()
    └── _process_consolidate(start_of_month - 2 months)
            │
            ├── SQL INSERT: one consolidated record per user/month
            │   (oldest old_value + newest new_value)
            │
            └── ORM unlink() of original non-consolidated records
                (with skip_karma_computation context to avoid
                 triggering user.karma recomputation)
```

---

## Bus Notifications

All gamification events send real-time notifications via `bus.bus`:

| Event | Channel | notif_type payload | Sender |
|-------|---------|-------------------|--------|
| Badge earned | user.partner_id | `badge` | `badge.user._send_badge()` |
| Rank up | user.partner_id | `level_up` | `res.users._rank_changed()` |
| Streak milestone | user.partner_id | `streak` | `streak._record_activity()` |
| Achievement unlock | user.partner_id | `achievement` | `achievement.unlock._grant_rewards()` |

All use channel type `"gamification/notification"` via bus._sendone.

Most use `user._send_gamification_notification(type, data)` which calls
`bus._sendone(user.partner_id, "gamification/notification", {type, ...data})`.

**Exception:** Badge-earned notifications go through `gamification.badge.user._send_badge()`,
which has its own bus notification logic separate from `_send_gamification_notification`.

---

## Security Model

### Access Control (ir.access.csv)

| Model | Employee (group_user) | Manager (group_erp_manager) | Portal | Public |
|-------|----------------------|----------------------------|--------|--------|
| goal | read, write | full CRUD | read, write | — |
| goal.definition | read | full CRUD | read | — |
| challenge | read | full CRUD | read | — |
| challenge.line | read | full CRUD | read | — |
| badge | read | full CRUD | read | read |
| badge.user | read, write, create | full CRUD | read, write, create | read |
| karma.rank | read | full CRUD (**group_system**) | read | read |
| karma.tracking | none | full CRUD (**group_system**) | none | — |
| streak.type | read | full CRUD | — | — |
| streak | read | full CRUD | — | — |
| kudos.category | read | full CRUD | — | — |
| kudos | read, write, create | full CRUD | — | — |
| achievement | read | full CRUD | — | — |
| achievement.unlock | read | full CRUD | — | — |
| team | read | full CRUD | — | — |
| engagement.snapshot | read | full CRUD | — | — |
| activity | read | full CRUD | — | — |
| mentorship | read, write, create | full CRUD | — | — |
| quest | read | full CRUD | — | — |
| quest.step | read | full CRUD | — | — |
| quest.enrollment | read, write, create | full CRUD | — | — |
| quest.step.completion | read, write, create | full CRUD | — | — |
| season | read | full CRUD | — | — |
| skill.tree | read | full CRUD | — | — |
| skill.node | read | full CRUD | — | — |
| skill.node.unlock | read | full CRUD | — | — |

### Row-Level Rules (ir.access)

| Rule XML ID | Model | Effect |
|-------------|-------|--------|
| `goal_user_visibility` | goal | Users see own goals + ranking-mode challenge goals |
| `goal_gamification_manager_visibility` | goal | Managers see all goals |
| `goal_global_multicompany` | goal | Filter by user's company |
| `streak_user_write` | streak | Users can only modify own streaks |
| `kudos_user_write` | kudos | Users can only modify own sent kudos |

---

## Dashboard Data Aggregation

`res.users.get_gamification_dashboard_data()` is designed as a single RPC
round-trip to populate the OWL dashboard component. It returns:

```python
{
    "profile": {
        "user_name", "karma", "rank_name", "rank_image",
        "next_rank_name", "xp_progress_percent", "xp_to_next_rank",
        "gold_badge", "silver_badge", "bronze_badge",
        "featured_badges": [{"id", "badge_name", "level"}...],
        "visibility",
    },
    "streaks": [{
        "id", "name", "current_count", "longest_count",
        "state", "freeze_remaining",
    }...],
    "goals": [{
        "id", "challenge_name", "definition_name", "current",
        "target", "completeness", "state", "end_date",
    }...],
    "badges": [{
        "id", "badge_name", "level", "date", "sender_name",
    }...],
    "activity_feed": [{
        "id", "activity_type", "user_name", "target_user_name",
        "summary", "icon", "karma_gained", "date",
    }...],
    "achievements": [{
        "id", "name", "description", "rarity", "date",
    }...],
    "leaderboard": [{
        "user_id", "user_name", "karma", "rank_name", "is_current_user",
    }...],
}
```

### Additional RPC Methods

| Method | Model | Purpose |
|--------|-------|---------|
| `get_activity_feed(limit=30)` | `gamification.activity` | Unified feed with privacy filtering |
| `get_analytics_summary()` | `gamification.engagement.snapshot` | Latest metrics + 7-day trends |
| `_get_karma_leaderboard(limit=10)` | `res.users` | Top karma users (privacy-filtered) |
| `send_kudos_from_dashboard(recipient_id, category_id, message)` | `res.users` | Create kudos from dashboard inline form |
| `get_season_leaderboard(limit=10)` | `gamification.season` | Karma earned during season window (**instance method**, requires specific record — not `@api.model`). **Not called from any shipped UI** — only from tests; not one of `gamification_dashboard.js`'s 3 `orm.call`s, unlike the four rows above (which the dashboard aggregation method calls internally). A future season-leaderboard widget is this method's intended consumer. |
| `get_suggested_mentors(limit=5)` | `gamification.mentorship` | Higher-karma users available for mentoring. **Not called from any shipped UI** — only from tests; not one of `gamification_dashboard.js`'s 3 `orm.call`s. A future mentor-suggestion widget is this method's intended consumer. |

---

## Quest Lifecycle

```
1. Admin creates quest with steps (ordered, prerequisite-linked)
   ├── Each step references a goal.definition + target
   ├── Steps can require prerequisite steps
   └── Quest has completion badge + karma reward

2. User enrolls → quest.enrollment (state=in_progress)

3. User completes steps in order:
   enrollment.complete_step(step)
       ├── Validate prerequisites (all prereq steps completed)
       ├── Create quest.step.completion record
       ├── Grant step karma + badge rewards
       └── Check if all steps done → auto-complete quest

4. Quest auto-completes:
   enrollment._complete_quest()
       ├── state = completed
       ├── Grant quest-level karma + badge
       └── Log to activity feed
```

---

## Skill Tree Unlock Flow

```
skill.node.unlock_for_user(user)
    │
    ├── check_unlock_for_user(user):
    │       ├── Not already unlocked?
    │       ├── All prerequisite nodes unlocked?
    │       ├── Karma >= threshold?
    │       └── Required quest completed?
    │
    ├── Create skill.node.unlock record
    ├── Grant karma reward
    ├── Grant badge reward
    └── Log to activity feed
```

---

## Season Lifecycle

```
draft ──→ active ──→ ended ──→ archived
            │
            ├── Challenges linked via season_id
            ├── Exclusive badges via season_badge_rel
            ├── Season leaderboard: karma earned between start/end dates
            └── Fresh leaderboard solves "permanent bottom-half" problem
```

---

## Engagement Nudge Pipeline

**Cron:** `ir_cron_engagement_nudges` — runs daily at 09:00

```
_cron_engagement_nudges()
    │
    ├── _nudge_streak_warning()
    │       Users with active streaks >= 3 days, 0 freeze remaining
    │       → "Streak at Risk!" notification
    │
    ├── _nudge_close_to_rank()
    │       Users within 10% of next rank's karma threshold
    │       → "Almost There!" notification
    │
    ├── _nudge_goals_almost_done()
    │       Goals >= 80% and < 100% complete, still in progress
    │       → "So Close!" notification
    │
    └── _nudge_inactive_users()
            Users who had karma activity 7-30 days ago but none in last 7 days
            → "We Miss You!" notification
```

---

## Adaptive Difficulty

```
challenge._get_adaptive_targets()
    │
    ├── Only for recurring challenges (period != 'once')
    │
    └── For each user × line:
            ├── Get last 3 closed goals
            ├── Compute avg completion rate
            ├── If avg > 90% → increase target by 15%
            ├── If avg < 50% → decrease target by 15% (min 1)
            └── Return {(user_id, line_id): adjusted_target}
```

---

## Activity Feed Integration

All gamification events auto-create `gamification.activity` records:

| Source | Trigger Point | Activity Type |
|--------|--------------|---------------|
| `gamification.kudos` | `create()` | `kudos` |
| `gamification.badge.user` | `_send_badge()` | `badge` |
| `gamification.achievement.unlock` | `_grant_rewards()` | `achievement` |
| `gamification.streak` | `_record_activity()` on milestones | `streak_milestone` |
| `res.users` | `_rank_changed()` | `level_up` |
| `gamification.quest.enrollment` | `_complete_quest()` | `challenge_completed` |
| `gamification.skill.node` | `unlock_for_user()` | `achievement` |

The feed respects `gamification_visibility` — activities from users with
`visibility='private'` are excluded from `get_activity_feed()`.

---

## Privacy / Visibility Controls

Users set `gamification_visibility` on their profile:

| Setting | Leaderboard | Activity Feed | Dashboard Profile |
|---------|-------------|---------------|-------------------|
| `public` | Visible | Visible | Visible |
| `team` | Visible | Visible | Visible |
| `private` | **Hidden** | **Hidden** | Self only |

Enforced in:
- `res.users._get_karma_leaderboard()` — filters out private users
- `gamification.activity.get_activity_feed()` — filters out private users' activities
- `gamification.season.get_season_leaderboard()` — uses same SQL patterns
