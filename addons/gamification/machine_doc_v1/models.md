# Gamification Models

## Model Relationship Diagram

```
gamification.challenge
    ├── line_ids ──→ gamification.challenge.line
    │                   └── definition_id ──→ gamification.goal.definition
    ├── user_ids ──→ res.users (m2m)
    ├── invited_user_ids ──→ res.users (m2m)
    ├── team_ids ──→ gamification.team (m2m)
    ├── report_message_group_id ──→ discuss.channel
    ├── report_template_id ──→ mail.template
    └── reward_id / reward_first_id / reward_second_id / reward_third_id ──→ gamification.badge

gamification.goal
    ├── definition_id ──→ gamification.goal.definition
    ├── user_id ──→ res.users
    ├── line_id ──→ gamification.challenge.line
    └── challenge_id (related via line_id)

gamification.badge
    ├── owner_ids ──→ gamification.badge.user
    │                   ├── user_id ──→ res.users
    │                   └── badge_id ──→ gamification.badge
    ├── challenge_ids ──→ gamification.challenge (o2m via reward_id)
    └── goal_definition_ids ──→ gamification.goal.definition (m2m)

gamification.karma.rank
    └── user_ids ──→ res.users (rank_id)

gamification.karma.tracking
    └── user_id ──→ res.users

gamification.kudos
    ├── sender_id ──→ res.users
    ├── recipient_id ──→ res.users
    └── category_id ──→ gamification.kudos.category

gamification.streak
    ├── user_id ──→ res.users
    └── streak_type_id ──→ gamification.streak.type

gamification.achievement
    └── unlock_ids ──→ gamification.achievement.unlock
                        ├── user_id ──→ res.users
                        └── achievement_id ──→ gamification.achievement

gamification.team
    ├── member_ids ──→ res.users (m2m)
    ├── captain_id ──→ res.users
    └── challenge_ids ──→ gamification.challenge (m2m)

gamification.activity
    ├── user_id ──→ res.users
    ├── target_user_id ──→ res.users
    ├── badge_id ──→ gamification.badge
    ├── achievement_id ──→ gamification.achievement
    └── challenge_id ──→ gamification.challenge

gamification.engagement.snapshot
    └── company_id ──→ res.company

gamification.mentorship
    ├── mentor_id ──→ res.users
    ├── mentee_id ──→ res.users
    └── completion_badge_id ──→ gamification.badge

gamification.quest
    ├── step_ids ──→ gamification.quest.step
    │                   ├── definition_id ──→ gamification.goal.definition
    │                   ├── prerequisite_ids ──→ gamification.quest.step (m2m)
    │                   └── skill_node_id ──→ gamification.skill.node
    ├── enrollment_ids ──→ gamification.quest.enrollment
    │                       └── completion_ids ──→ gamification.quest.step.completion
    ├── reward_badge_id ──→ gamification.badge
    └── (via season) season_id on challenge ──→ gamification.season

gamification.season
    ├── challenge_ids ──→ gamification.challenge (o2m via season_id)
    ├── badge_ids ──→ gamification.badge (m2m)
    └── quest_ids ──→ gamification.quest (m2m)

gamification.skill.tree
    └── node_ids ──→ gamification.skill.node
                        ├── prerequisite_ids ──→ gamification.skill.node (m2m)
                        ├── quest_id ──→ gamification.quest
                        ├── badge_id ──→ gamification.badge
                        └── unlock_ids ──→ gamification.skill.node.unlock

res.users (extended)
    ├── karma (computed from karma_tracking_ids)
    ├── rank_id ──→ gamification.karma.rank
    ├── next_rank_id ──→ gamification.karma.rank
    ├── badge_ids ──→ gamification.badge.user
    ├── streak_ids ──→ gamification.streak
    ├── featured_badge_ids ──→ gamification.badge.user (m2m)
    └── gamification_visibility (selection: private/team/public)
```

---

## 1. gamification.challenge

**File:** `models/gamification_challenge.py`
**Inherits:** `mixin.mail.thread`
**Description:** Set of predefined objectives with recurrence rules and rewards.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate | Challenge name |
| `description` | Text | translate | Long description |
| `state` | Selection | `draft/inprogress/done`, tracking | Lifecycle state |
| `manager_id` | Many2one `res.users` | default=uid | Responsible user |
| `user_ids` | Many2many `res.users` | | Explicit participants |
| `user_domain` | Char | | Alternative domain-based participants |
| `user_count` | Integer | computed | # participants |
| `period` | Selection | `once/daily/weekly/monthly/yearly`, required | Recurrence |
| `start_date` | Date | | Period start |
| `end_date` | Date | | Period end |
| `line_ids` | One2many `challenge.line` | required, copy | Goal templates |
| `reward_id` | Many2one `badge` | | Badge for every succeeder |
| `reward_first_id` | Many2one `badge` | | Badge for 1st place |
| `reward_second_id` | Many2one `badge` | | Badge for 2nd place |
| `reward_third_id` | Many2one `badge` | | Badge for 3rd place |
| `reward_failure` | Boolean | | Reward bests even if not succeeded |
| `reward_realtime` | Boolean | default=True | Grant badge immediately on goal completion |
| `visibility_mode` | Selection | `personal/ranking`, required | Individual or leaderboard |
| `challenge_mode` | Selection | `individual/team`, required | Competition mode |
| `team_ids` | Many2many `team` | | Competing teams |
| `invited_user_ids` | Many2many `res.users` | | Suggested challenge participants |
| `report_message_frequency` | Selection | `never/onchange/daily/weekly/monthly/yearly`, required | Report frequency |
| `report_message_group_id` | Many2one `discuss.channel` | | Channel for report copies |
| `report_template_id` | Many2one `mail.template` | required | Email template for reports |
| `remind_update_delay` | Integer | | Days before reminder for manual goals |
| `last_report_date` | Date | default=today | Last report sent |
| `next_report_date` | Date | computed, stored | Next scheduled report |
| `challenge_category` | Selection | `hr/other`, required | Menu visibility |

### State Machine

```
draft ──→ inprogress ──→ done
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `action_start()` | Transition draft → inprogress, generate goals |
| `action_check()` | Update goals and generate reports |
| `action_report_progress()` | Send progress report to participants |
| `_update_all()` | Full cycle: add users from domain, generate goals, update, close expired |
| `_cron_update()` | Entry point for daily cron |
| `_generate_goals_from_challenge()` | Create goal records for each user × line |
| `report_progress()` | Generate and send challenge report emails |
| `accept_challenge()` | User accepts a suggested challenge |
| `discard_challenge()` | User discards a suggested challenge |
| `_check_challenge_reward()` | Grant badges for challenge completion/ranking |
| `_recompute_challenge_users()` | Refresh user list from user_domain |
| `start_end_date_for_period()` | Module-level helper returning (start, end) dates |

---

## 2. gamification.challenge.line

**File:** `models/gamification_challenge_line.py`
**Description:** Goal template within a challenge — one line generates one goal per participant.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `challenge_id` | Many2one `challenge` | required, ondelete=cascade | Parent challenge |
| `definition_id` | Many2one `goal.definition` | required | What to measure |
| `target_goal` | Float | required | Target value |
| `sequence` | Integer | | Ordering |
| `name` | Char | related to definition | Display name |
| `condition` | Selection | related to definition | higher/lower |

---

## 3. gamification.goal

**File:** `models/gamification_goal.py`
**Inherits:** `mixin.mail.thread`
**Description:** Individual goal instance for a user in a specific time period.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `definition_id` | Many2one `goal.definition` | required, ondelete=cascade | What to measure |
| `user_id` | Many2one `res.users` | required, indexed, ondelete=cascade | Participant |
| `line_id` | Many2one `challenge.line` | ondelete=cascade | Source template |
| `challenge_id` | Many2one | related via line_id, stored, indexed | Parent challenge |
| `start_date` | Date | default=today | Period start |
| `end_date` | Date | | Period end |
| `target_goal` | Float | required | Target value |
| `current` | Float | required, default=0 | Current value |
| `completeness` | Float | computed | 0-100% completion |
| `state` | Selection | `draft/inprogress/reached/failed/canceled` | Goal state |
| `to_update` | Boolean | | Needs manual update |
| `closed` | Boolean | | Goal finalized |
| `color` | Integer | computed | 0/2(failed late)/5(reached late) |

### State Machine

```
draft ──→ inprogress ──→ reached
                    └──→ failed (closed=True)
Note: "canceled" exists as a state value but no method transitions to it;
action_cancel() resets state back to inprogress.
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `update_goal()` | Recompute value based on computation_mode (manually/count/sum/python) |
| `_get_write_values(new_value)` | Compare value to target, determine state transition |
| `_check_remind_delay()` | Send reminder email for stale manual goals |
| `get_action()` | Return action dict to update goal (wizard or linked action) |
| `action_start()` | Transition draft → inprogress, call update_goal() |
| `action_reach()` | Mark goal as reached |
| `action_fail()` | Mark goal as failed |
| `action_cancel()` | Reset reached/failed back to inprogress |

---

## 4. gamification.goal.definition

**File:** `models/gamification_goal_definition.py`
**Description:** Template defining how a goal is evaluated.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate | Goal name |
| `computation_mode` | Selection | `manually/count/sum/python`, required | How to compute |
| `display_mode` | Selection | `progress/boolean` | Numeric or done/not-done |
| `model_id` | Many2one `ir.model` | | Target model (for count/sum) |
| `field_id` | Many2one `ir.model.fields` | | Field to sum |
| `field_date_id` | Many2one `ir.model.fields` | | Date field for period filter |
| `domain` | Char | required, default=`[]` | ORM domain (may reference `user`) |
| `batch_mode` | Boolean | | Evaluate in batch vs per-user |
| `batch_distinctive_field` | Many2one `ir.model.fields` | | Field distinguishing users in batch |
| `batch_user_expression` | Char | | Expression to identify user in batch |
| `compute_code` | Text | | Python code for `python` mode |
| `condition` | Selection | `higher/lower`, required | Goal direction |
| `monetary` | Boolean | | Values in company currency |
| `suffix` | Char | translate | Unit label (e.g., "leads") |
| `full_suffix` | Char | computed | Currency symbol + suffix combined |
| `action_id` | Many2one `ir.actions.act_window` | | Linked action for manual update |
| `res_id_field` | Char | | Field on res.users for action context |

### Key Methods

| Method | Purpose |
|--------|---------|
| `_compute_full_suffix()` | Combine currency symbol + suffix |
| `_check_domain_validity()` | Validate domain syntax via test search_count |
| `_check_model_validity()` | Verify field exists and is stored |
| `create()` | Validates domain and model on creation |
| `write()` | Re-validates domain/model when relevant fields change |

---

## 5. gamification.badge

**File:** `models/gamification_badge.py`
**Inherits:** `mixin.mail.thread`, `mixin.image`
**Description:** Achievement award that users can send and receive.

### Grant Status Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `CAN_GRANT` | 1 | User is allowed |
| `NOBODY_CAN_GRANT` | 2 | Badge rule_auth = nobody |
| `USER_NOT_VIP` | 3 | User not in authorized list |
| `BADGE_REQUIRED` | 4 | User lacks prerequisite badges |
| `TOO_MANY` | 5 | Monthly limit exceeded |

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate | Badge name |
| `level` | Selection | `bronze/silver/gold` | Forum badge level |
| `rule_auth` | Selection | `everyone/users/having/nobody`, required | Who can grant |
| `rule_auth_user_ids` | Many2many `res.users` | | Authorized givers (rule_auth=users) |
| `rule_auth_badge_ids` | Many2many `badge` | | Required badges (rule_auth=having) |
| `rule_max` | Boolean | | Monthly limit enabled |
| `rule_max_number` | Integer | | Max grants per person per month |
| `granted_count` | Integer | computed (SQL) | Total grants |
| `granted_users_count` | Integer | computed (SQL) | Unique recipients |
| `stat_this_month` | Integer | computed (SQL) | Monthly grants |
| `stat_my_monthly_sending` | Integer | computed (SQL) | Current user's monthly sends |
| `remaining_sending` | Integer | computed | Grants remaining (-1 = unlimited) |

### Key Methods

| Method | Purpose |
|--------|---------|
| `_can_grant_badge()` | Return status code (1-5) |
| `check_granting()` | Raise UserError if user cannot grant |
| `_compute_owner_stats()` | One SQL aggregation for owner, per-user and monthly stats |
| `_compute_remaining_sending()` | Compute remaining grants |

---

## 6. gamification.badge.user

**File:** `models/gamification_badge_user.py`
**Inherits:** `mixin.mail.thread`
**Description:** Instance of a badge granted to a user.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `user_id` | Many2one `res.users` | required, indexed, ondelete=cascade | Recipient |
| `sender_id` | Many2one `res.users` | | Who granted |
| `badge_id` | Many2one `badge` | required, indexed, ondelete=cascade | Which badge |
| `challenge_id` | Many2one `challenge` | | Challenge that triggered |
| `comment` | Text | | Grant comment |
| `level` | Selection | related to badge.level, stored | Denormalized level |

### Key Methods

| Method | Purpose |
|--------|---------|
| `_send_badge()` | Send notification email + bus notification |
| `create()` | Validates badge granting rights via `check_granting()` |

---

## 7. gamification.karma.rank

**File:** `models/gamification_karma_rank.py`
**Inherits:** `mixin.image`
**Description:** Level thresholds in the karma progression system.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Text | required, translate | Rank name (e.g., "Master") |
| `description` | Html | translate | Shown on profile |
| `description_motivational` | Html | translate | Motivational text |
| `description_perks` | Html | translate | Unlocked perks |
| `karma_min` | Integer | required, default=1, CHECK > 0 | XP threshold |
| `level_number` | Integer | default=0 | Sequential level display |
| `unlock_badge_ids` | Many2many `badge` | | Auto-granted on rank-up |
| `user_ids` | One2many `res.users` | | Users at this rank |
| `rank_users_count` | Integer | computed | Count |

### Default Ranks (data)

| Rank | karma_min |
|------|-----------|
| Newbie | 1 |
| Student | 100 |
| Bachelor | 500 |
| Master | 2000 |
| Doctor | 10000 |

### Key Methods

| Method | Purpose |
|--------|---------|
| `create()` | Triggers rank recomputation for affected users |
| `write()` | Reranks users when karma_min changes |

---

## 8. gamification.karma.tracking

**File:** `models/gamification_karma_tracking.py`
**Description:** Audit log of karma changes. Source of truth for user karma.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `user_id` | Many2one `res.users` | required, indexed, ondelete=cascade | User |
| `old_value` | Integer | readonly | Karma before |
| `new_value` | Integer | required | Karma after |
| `gain` | Integer | computed (new - old) | Delta |
| `consolidated` | Boolean | | Part of monthly rollup |
| `tracking_date` | Datetime | default=now, indexed | When |
| `reason` | Text | default="Add Manually" | Human description |
| `origin_ref` | Reference | `res.users`, `gamification.streak`, `gamification.kudos`, `gamification.achievement.unlock` | Source record |
| `origin_ref_model_name` | Selection | computed, stored | Model type of origin |

### Key Methods

| Method | Purpose |
|--------|---------|
| `create()` | Auto-fills old_value from current user karma |
| `_consolidate_cron()` | Monthly cron: merge old trackings into single records |
| `_process_consolidate(from_date, end_date=None)` | SQL INSERT + ORM unlink for monthly consolidation |

---

## 9. gamification.kudos + gamification.kudos.category

**File:** `models/gamification_kudos.py`

### gamification.kudos.category

**Description:** Category for peer recognition (e.g., Teamwork, Innovation).

| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Category name |
| `icon` | Char | Font Awesome class |
| `karma_granted` | Integer | Karma auto-granted to recipient |
| `kudos_count` | Integer | Computed count |

### gamification.kudos

**Inherits:** `mixin.mail.thread`
**Description:** Peer-to-peer recognition message.

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `sender_id` | Many2one `res.users` | required, readonly, default=uid, ondelete=cascade | Sender |
| `recipient_id` | Many2one `res.users` | required, ondelete=cascade | Recipient |
| `category_id` | Many2one `kudos.category` | required, ondelete=restrict | Category |
| `message` | Text | required | Recognition message |
| `summary` | Char | computed, stored | Auto-generated one-liner |
| `karma_granted` | Integer | readonly | Karma actually granted |

### Key Methods

| Method | Purpose |
|--------|---------|
| `create()` | Validates no self-kudos, grants karma, posts to mail thread |

### Default Categories (data)

| Category | karma_granted | Icon |
|----------|---------------|------|
| Teamwork | 5 | `fa fa-users` |
| Innovation | 10 | `fa fa-lightbulb-o` |
| Quality | 5 | `fa fa-diamond` |
| Speed | 5 | `fa fa-bolt` |
| Mentorship | 10 | `fa fa-graduation-cap` |

---

## 10. gamification.streak.type + gamification.streak

**File:** `models/gamification_streak.py`

### gamification.streak.type

**Description:** Configurable streak type — defines what activity sustains the streak.

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate | Streak name |
| `model_id` | Many2one `ir.model` | required, ondelete=cascade | Target model |
| `domain` | Char | required, default=`[]` | Activity domain (refs: `user`, `date_from`, `date_to`) |
| `date_field_id` | Many2one `ir.model.fields` | required, ondelete=cascade | Date field to check |
| `karma_bonus` | Integer | default=0 | Daily karma bonus |
| `freeze_allowance` | Integer | default=2 | Skip days per month |

### STREAK_MILESTONES (module constant)

| Day | Karma Multiplier |
|-----|-----------------|
| 7 | 2x |
| 30 | 5x |
| 100 | 10x |
| 365 | 25x |

### gamification.streak

**Description:** Per-user streak instance tracking consecutive daily activity.

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `user_id` | Many2one `res.users` | required, indexed, ondelete=cascade | User |
| `streak_type_id` | Many2one `streak.type` | required, indexed, ondelete=cascade | Type |
| `current_count` | Integer | readonly | Current consecutive days |
| `longest_count` | Integer | readonly | All-time best |
| `last_activity_date` | Date | readonly | Last recorded day |
| `freeze_remaining` | Integer | | Freeze days left this month |
| `state` | Selection | `active/broken`, readonly, indexed | Current state |
| `total_karma_earned` | Integer | readonly | Cumulative karma from streak |

**Unique constraint:** `(user_id, streak_type_id)` — one streak per type per user.

### State Machine

```
active ←──→ broken
  (via _record_activity revives broken streaks)
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `_record_activity()` | Increment count, grant karma (with milestone multiplier) |
| `_break_streak()` | Reset current_count=0, state=broken, preserve longest |
| `_cron_update_streaks()` | Daily: check activity, use freeze or break, reset freeze on 1st |
| `_get_user_streaks(user)` | Create any missing streak records and return the user's whole set |

### gamification.streak.type Key Methods

| Method | Purpose |
|--------|---------|
| `_check_user_activity(user, check_date)` | Evaluate domain for given date, return True if match |
| `_compute_user_count()` | Count active streaks per type |

---

## 11. gamification.achievement + gamification.achievement.unlock

**File:** `models/gamification_achievement.py`

### gamification.achievement

**Description:** Hidden/discovery achievement unlocked through normal work.

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate | Achievement name |
| `description` | Text | translate | Shown after unlock |
| `hint` | Text | translate | Shown before unlock |
| `model_id` | Many2one `ir.model` | required, ondelete=cascade | Trigger model |
| `trigger_domain` | Char | required, default=`[]` | Domain (refs: `user`) |
| `trigger_count` | Integer | default=1 | Records needed to unlock |
| `badge_id` | Many2one `badge` | | Reward badge |
| `karma_reward` | Integer | default=0 | Reward karma |
| `rarity` | Selection | `common/rare/epic/legendary` | Rarity tier |
| `hidden` | Boolean | default=True | Mystery (name hidden until unlock) |
| `unlock_count` | Integer | computed | # users who unlocked |

### gamification.achievement.unlock

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `achievement_id` | Many2one | required, indexed, ondelete=cascade | Achievement |
| `user_id` | Many2one | required, indexed, ondelete=cascade | User |
| `unlock_date` | Datetime | readonly, default=now | When unlocked |
| `rarity` | Selection | related, stored | Denormalized |

**Unique constraint:** `(user_id, achievement_id)` — one unlock per user per achievement.

### Key Methods

| Method | Purpose |
|--------|---------|
| `_check_achievement_for_users(users)` | Evaluate trigger domain, create unlocks |
| `_cron_check_achievements()` | Daily: check all active achievements for all users |
| `_grant_rewards()` | (on unlock) Grant karma + badge + bus notification |

---

## 12. gamification.team

**File:** `models/gamification_team.py`
**Inherits:** `mixin.mail.thread`
**Description:** Team for collaborative challenges.

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate, tracking | Team name |
| `member_ids` | Many2many `res.users` | | Members |
| `captain_id` | Many2one `res.users` | | Team leader |
| `member_count` | Integer | computed | # members |
| `team_karma` | Integer | computed, stored | Sum of members' karma |
| `team_badges` | Integer | computed, stored | Total badges |
| `challenge_ids` | Many2many `challenge` | | Active challenges |

### Key Methods

| Method | Purpose |
|--------|---------|
| `get_team_challenge_score(challenge)` | Average completeness of members' goals |

---

## 13. res.users (extension)

**File:** `models/res_users.py`
**Description:** Extends base user model with gamification fields and methods.

### Added Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `karma` | Integer | computed (from tracking), stored, readonly=False | XP points |
| `karma_tracking_ids` | One2many `karma.tracking` | groups=system | Audit log |
| `badge_ids` | One2many `badge.user` | | Earned badges |
| `gold_badge` | Integer | computed (SQL) | Count |
| `silver_badge` | Integer | computed (SQL) | Count |
| `bronze_badge` | Integer | computed (SQL) | Count |
| `rank_id` | Many2one `karma.rank` | indexed | Current rank |
| `next_rank_id` | Many2one `karma.rank` | | Next rank |
| `xp_to_next_rank` | Integer | computed | XP remaining |
| `xp_progress_percent` | Float | computed | 0-100% progress |
| `streak_ids` | One2many `streak` | | User's streaks |

### Key Methods

| Method | Trigger | Purpose |
|--------|---------|---------|
| `_compute_karma()` | `karma_tracking_ids.new_value` | Sum of all recorded gains (`new_value - old_value`) per user |
| `_compute_badge_level_counts()` | `badge_ids` | SQL GROUP BY for gold/silver/bronze counts |
| `_compute_xp_progress()` | `karma, rank_id, next_rank_id` | Progress bar calculation |
| `_add_karma(gain, source, reason)` | explicit call | Create tracking record (single user) |
| `_add_karma_batch(values_per_user)` | explicit call | Create tracking records (batch) |
| `_recompute_rank()` | after karma change | Match user to rank tier: one query for the ranks, one write per distinct target rank |
| `_rank_changed()` | after rank change | Grant unlock badges + send notification |
| `_send_gamification_notification()` | various | Bus notification to user's partner |
| `get_gamification_dashboard_data()` | @api.model RPC | Aggregate all gamification data for dashboard |
| `_get_next_rank()` | explicit call | Return next karma rank for this user |
| `prepare_rank_email_links()` | extension hook | Add redirect buttons to rank-reached email |
| `action_karma_report()` | UI action | Open karma tracking list for this user |
| `_get_tracking_karma_gain_position()` | explicit call | Ranked karma gain in date range (SQL) |
| `_get_karma_position()` | explicit call | Absolute total-karma rank position (SQL) |
| `create()` | | Track initial karma via _add_karma_batch |
| `write()` | `karma` in vals | Track karma changes via _add_karma_batch |
| `_get_karma_leaderboard(limit=10)` | @api.model | Top karma users (privacy-filtered) |
| `send_kudos_from_dashboard(recipient_id, category_id, message)` | @api.model | Create kudos inline from dashboard |
| `_cron_engagement_nudges()` | @api.model cron | Detect patterns, send targeted notifications |
| `_nudge_streak_warning()` | internal | Warn users with 0 freeze days left |
| `_nudge_close_to_rank()` | internal | Notify users within 10% of next rank |
| `_nudge_goals_almost_done()` | internal | Notify users with >80% complete goals |
| `_nudge_inactive_users()` | internal | Re-engage users inactive for 7+ days |

---

## 14. gamification.activity

**File:** `models/gamification_activity.py`
**Inherits:** `mixin.mail.thread`
**Description:** Unified social feed for all gamification events.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `activity_type` | Selection | `badge/kudos/achievement/streak_milestone/level_up/challenge_completed`, required, indexed | Event type |
| `user_id` | Many2one `res.users` | required, indexed, ondelete=cascade | Who did/received |
| `target_user_id` | Many2one `res.users` | indexed, ondelete=set null | Secondary user (e.g. kudos recipient) |
| `company_id` | Many2one `res.company` | related to user, stored, indexed | Company filter |
| `summary` | Char | required | Human-readable one-liner |
| `icon` | Char | | Font Awesome CSS class |
| `activity_date` | Datetime | default=now, indexed | When |
| `badge_id` | Many2one `badge` | ondelete=set null | Source badge (if applicable) |
| `achievement_id` | Many2one `achievement` | ondelete=set null | Source achievement |
| `challenge_id` | Many2one `challenge` | ondelete=set null | Source challenge |
| `karma_gained` | Integer | | Karma earned in this event |

### Key Methods

| Method | Purpose |
|--------|---------|
| `_log_badge(user, badge, sender)` | Record badge-earned activity |
| `_log_kudos(sender, recipient, category, karma)` | Record kudos-sent activity |
| `_log_achievement(user, achievement, karma)` | Record achievement-unlocked activity |
| `_log_streak_milestone(user, streak_type, day_count, karma)` | Record streak milestone |
| `_log_level_up(user, rank)` | Record level-up activity |
| `_log_challenge_completed(user, challenge)` | Record challenge completion |
| `get_activity_feed(limit=30)` | Return formatted feed (privacy-filtered) |

---

## 15. gamification.engagement.snapshot

**File:** `models/gamification_engagement.py`
**Description:** Daily snapshot of gamification engagement metrics.

### Fields (25+ metrics across 6 categories)

| Category | Fields |
|----------|--------|
| Users | `total_users`, `users_with_karma`, `active_users_7d`, `active_users_30d` |
| Goals | `active_challenges`, `goals_in_progress`, `goals_reached_7d`, `goal_completion_rate` |
| Badges | `total_badges_granted`, `badges_granted_7d`, `unique_badge_holders` |
| Kudos | `total_kudos`, `kudos_7d`, `unique_kudos_senders_7d`, `unique_kudos_recipients_7d` |
| Streaks | `active_streaks`, `broken_streaks`, `avg_streak_length`, `streaks_past_7d`, `streaks_past_30d` |
| Karma | `total_karma_granted`, `karma_granted_7d`, `avg_user_karma` |

**Unique:** `(snapshot_date, company_id)` — one per company per day.

### Key Methods

| Method | Purpose |
|--------|---------|
| `_cron_record_snapshot()` | Daily cron: record snapshot for each company |
| `_record_snapshot(company)` | Compute and store metrics (idempotent) |
| `get_analytics_summary()` | Return latest + 7-day trend comparison |

---

## 16. gamification.mentorship

**File:** `models/gamification_mentorship.py`
**Inherits:** `mixin.mail.thread`
**Description:** Mentor/mentee pairing with karma incentives.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `mentor_id` | Many2one `res.users` | required, indexed, tracking | Mentor |
| `mentee_id` | Many2one `res.users` | required, indexed, tracking | Mentee |
| `state` | Selection | `pending/active/completed/cancelled`, tracking, indexed | Lifecycle. Starts `pending`: rewards only accrue once the counterparty accepts, so an employee cannot appoint themselves mentor and collect on the mentee's rank-ups |
| `start_date` | Date | default=today, readonly | When started |
| `end_date` | Date | tracking | When ended |
| `description` | Text | | Goals |
| `mentor_karma_per_milestone` | Integer | default=25 | Karma per mentee rank-up |
| `mentor_karma_on_completion` | Integer | default=100 | Karma bonus on completion |
| `mentee_milestones_reached` | Integer | readonly | Counter |
| `total_mentor_karma` | Integer | readonly | Cumulative |
| `completion_badge_id` | Many2one `badge` | | Badge for both on completion |

**Unique:** `(mentor_id, mentee_id) WHERE state != 'cancelled'`

### State Machine

```
pending ──→ active ──→ completed (with rewards)
   │            └──→ cancelled
   └──→ cancelled
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `_compute_display_name()` | Show "X mentoring Y" |
| `_check_not_self_mentoring()` | Constraint: prevent self-mentoring |
| `action_complete()` | End mentorship, grant karma + badge to both |
| `action_cancel()` | Cancel mentorship |
| `_on_mentee_rank_up(mentee)` | Called by `_rank_changed()` — grants mentor karma |
| `get_suggested_mentors(limit=5)` | Return higher-karma users for current user |

---

## 17. gamification.quest (+ step, enrollment, step.completion)

**File:** `models/gamification_quest.py`
**Inherits:** `mixin.mail.thread` (quest only)
**Description:** Multi-step narrative journeys.

### gamification.quest

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate, tracking | Quest name |
| `description` | Html | translate | Story/narrative |
| `sequence` | Integer | default=10 | Ordering |
| `active` | Boolean | default=True | Archivable |
| `icon` | Image | max 128x128 | Quest icon |
| `step_ids` | One2many `quest.step` | copy | Ordered steps |
| `step_count` | Integer | computed | # steps |
| `reward_badge_id` | Many2one `badge` | | Completion badge |
| `reward_karma` | Integer | default=0 | Completion karma bonus |
| `quest_mode` | Selection | `solo/team` | Mode |
| `difficulty` | Selection | `beginner/intermediate/advanced/expert` | Difficulty |
| `enrollment_ids` | One2many `quest.enrollment` | | User enrollments |
| `enrollment_count` | Integer | computed | # enrolled |
| `completion_count` | Integer | computed | # completed |

### gamification.quest.step

| Field | Type | Purpose |
|-------|------|---------|
| `quest_id` | Many2one `quest` | Parent |
| `name` | Char | Step name |
| `description` | Text | What to do (translate) |
| `sequence` | Integer | Ordering |
| `definition_id` | Many2one `goal.definition` | What to accomplish |
| `target_goal` | Float | Target value |
| `prerequisite_ids` | Many2many `quest.step` | Must complete before |
| `karma_reward` | Integer | Per-step karma |
| `badge_id` | Many2one `badge` | Per-step badge |
| `skill_node_id` | Many2one `skill.node` | Linked skill tree node |

**Constraint:** `_check_no_self_prerequisite` — a step cannot be its own prerequisite.

### gamification.quest.enrollment

| Field | Type | Purpose |
|-------|------|---------|
| `quest_id` | Many2one `quest` | Which quest |
| `user_id` | Many2one `res.users` | Who |
| `state` | Selection | `in_progress/completed/abandoned` |
| `progress_percent` | Float | Computed: done steps / total steps |
| `completion_ids` | One2many `step.completion` | Step records |

**Unique:** `(user_id, quest_id)`

### gamification.quest.step.completion

| Field | Type | Purpose |
|-------|------|---------|
| `enrollment_id` | Many2one `quest.enrollment` | Which enrollment |
| `step_id` | Many2one `quest.step` | Which step |
| `completion_date` | Datetime | When completed (default=now, readonly) |

**Unique:** `(enrollment_id, step_id)`

### Key Methods

| Method | Model | Purpose |
|--------|-------|---------|
| `step_count`, `enrollment_count` | quest | `fields.Count` over `step_ids` / `enrollment_ids` |
| `_compute_completion_count()` | quest | Count completed enrollments |
| `complete_step(step)` | quest.enrollment | Validate state + prereqs, create completion, grant rewards, check quest done |
| `_complete_quest()` | quest.enrollment | Grant quest rewards, log to feed |
| `action_abandon()` | quest.enrollment | Set state to abandoned |

---

## 18. gamification.season

**File:** `models/gamification_season.py`
**Inherits:** `mixin.mail.thread`
**Description:** Time-limited themed event with exclusive rewards.

### Fields

| Field | Type | Key Attributes | Purpose |
|-------|------|----------------|---------|
| `name` | Char | required, translate, tracking | Season name |
| `description` | Html | translate | Description |
| `theme` | Char | translate | Visual theme/motto |
| `state` | Selection | `draft/active/ended/archived`, tracking, indexed | Lifecycle |
| `start_date` | Date | required, tracking | Period start |
| `end_date` | Date | required, tracking | Period end |
| `icon` | Image | max 128x128 |
| `challenge_ids` | One2many `challenge` via `season_id` | Season challenges |
| `badge_ids` | Many2many `badge` | Exclusive badges |
| `quest_ids` | Many2many `quest` | Season quests |
| `challenge_count` | Integer | computed | # challenges |
| `participant_count` | Integer | computed | # unique participants |

### State Machine

```
draft ──→ active ──→ ended ──→ archived
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `action_activate()` | Start the season |
| `action_end()` | End the season |
| `action_archive()` | Archive completed season |
| `get_season_leaderboard(limit=10)` | Karma earned during season window (SQL, **instance method** — not `@api.model`) |

---

## 19. gamification.skill.tree + skill.node + skill.node.unlock

**File:** `models/gamification_skill.py`
**Description:** Branching progression paths with prerequisite edges.

### gamification.skill.tree

| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Tree name (e.g., "Sales Mastery") |
| `description` | Text | What this tree covers |
| `sequence` | Integer | Ordering |
| `active` | Boolean | Archivable |
| `icon` | Image | Tree icon |
| `color` | Integer | Color index |
| `node_ids` | One2many `skill.node` | All nodes in tree |
| `node_count` | Integer | Computed count |

### gamification.skill.node

| Field | Type | Purpose |
|-------|------|---------|
| `tree_id` | Many2one `skill.tree` | Parent tree |
| `name` | Char | Skill name |
| `level` | Integer | Vertical position in tree |
| `prerequisite_ids` | Many2many `skill.node` | Must unlock before |
| `dependent_ids` | Many2many `skill.node` | What this unlocks (inverse) |
| `karma_threshold` | Integer | Min karma required |
| `quest_id` | Many2one `quest` | Required quest completion |
| `karma_reward` | Integer | Karma on unlock |
| `badge_id` | Many2one `badge` | Badge on unlock |
| `unlock_ids` | One2many `skill.node.unlock` | Tracking |
| `unlock_count` | Integer | Computed count |
| `sequence` | Integer | Ordering within level |

### gamification.skill.node.unlock

| Field | Type | Purpose |
|-------|------|---------|
| `node_id` | Many2one `skill.node` | Which node |
| `user_id` | Many2one `res.users` | Who unlocked |
| `unlock_date` | Datetime | When |

**Unique:** `(user_id, node_id)`

### Key Methods

| Method | Purpose |
|--------|---------|
| `check_unlock_for_user(user)` | Verify all conditions (prereqs, karma, quest) |
| `unlock_for_user(user)` | Create unlock, grant rewards, log to feed |
