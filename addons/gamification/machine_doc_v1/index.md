# Gamification Module — Machine Documentation v1

## Purpose

Best-in-class employee engagement platform: goals, badges, karma progression,
peer recognition (kudos), streaks, hidden achievements, teams, multi-step
quests, skill trees, seasonal events, mentorship, engagement analytics,
adaptive difficulty, and smart nudges.

## Module Metadata

| Key | Value |
|-----|-------|
| Technical name | `gamification` |
| Category | Productivity |
| Dependencies | `mail` |
| Python models | 26 (across 19 files) + 2 wizards |
| Views | 20 XML files |
| Wizards | 2 transient models |
| Cron jobs | 8 |
| Test files | 19 (common + 18 test modules) |
| Total tests | 271 (`--test-tags /gamification`) |
| OWL components | 2 (dashboard + notification service) |

## File Inventory

### Models (`models/`)

| File | Models | Purpose |
|------|--------|---------|
| `gamification_challenge.py` | `gamification.challenge` | Challenge orchestration, adaptive difficulty |
| `gamification_challenge_line.py` | `gamification.challenge.line` | Goal template within challenge |
| `gamification_goal.py` | `gamification.goal` | Individual goal instance |
| `gamification_goal_definition.py` | `gamification.goal.definition` | Goal computation template |
| `gamification_badge.py` | `gamification.badge` | Badge with granting rules |
| `gamification_badge_user.py` | `gamification.badge.user` | Badge grant instance |
| `gamification_karma_rank.py` | `gamification.karma.rank` | XP rank thresholds |
| `gamification_karma_tracking.py` | `gamification.karma.tracking` | Karma audit log |
| `gamification_kudos.py` | `gamification.kudos.category`, `gamification.kudos` | Peer recognition |
| `gamification_streak.py` | `gamification.streak.type`, `gamification.streak` | Daily activity streaks |
| `gamification_achievement.py` | `gamification.achievement`, `gamification.achievement.unlock` | Hidden achievements |
| `gamification_team.py` | `gamification.team` | Team competition |
| `gamification_activity.py` | `gamification.activity` | Unified social activity feed |
| `gamification_engagement.py` | `gamification.engagement.snapshot` | Daily engagement analytics |
| `gamification_mentorship.py` | `gamification.mentorship` | Mentor/mentee pairing |
| `gamification_quest.py` | `gamification.quest`, `.quest.step`, `.quest.enrollment`, `.quest.step.completion` | Multi-step narrative journeys |
| `gamification_season.py` | `gamification.season` | Time-limited themed events |
| `gamification_skill.py` | `gamification.skill.tree`, `.skill.node`, `.skill.node.unlock` | Branching skill progression |
| `res_users.py` | extends `res.users` | Karma, ranks, profile, leaderboard, nudges |

### Wizards (`wizards/`)

| File | Model | Purpose |
|------|-------|---------|
| `update_goal.py` | `gamification.goal.wizard` | Manual goal value update |
| `grant_badge.py` | `gamification.badge.user.wizard` | Grant badge to user |

### Tests (`tests/`)

| File | Classes | Coverage Area |
|------|---------|---------------|
| `common.py` | `HttpCaseGamification`, `TransactionCaseGamification` | Base setup (demo user with 2500 karma) |
| `test_challenge.py` | `TestGamificationCommon`, `test_challenge`, `TestChallengeRewardNobodyBadge`, `test_badge_wizard` | Challenge lifecycle, goal generation, badge rewards |
| `test_karma_tracking.py` | `TestKarmaTrackingCommon`, `TestComputeRankCommon` | Karma gain, consolidation, rank computation |
| `test_kudos.py` | `TestKudos` | Kudos creation, karma grants, self-prevention |
| `test_streak.py` | `TestStreakCommon`, `TestStreak` | Streak recording, freeze, break, milestones, cron |
| `test_achievement.py` | `TestAchievement` | Trigger evaluation, unlock uniqueness, rewards |
| `test_badge.py` | `TestBadgeGranting` | All 5 grant rules, monthly limits, stats |
| `test_team.py` | `TestTeam` | Team stats, challenge scoring |
| `test_engagement.py` | `TestEngagementSnapshot`, `TestDashboardEnhancements`, `TestProfileEnhancements` | Analytics snapshots, leaderboard, send-kudos, featured badges |
| `test_activity_feed.py` | `TestActivityFeed` | Activity auto-creation from kudos/badges/achievements/level-ups |
| `test_mentorship.py` | `TestMentorship` | Mentorship lifecycle, karma rewards, suggested mentors |
| `test_quest.py` | `TestQuest`, `TestSeason`, `TestSkillTree` | Quest steps/prerequisites, season lifecycle, skill node unlocking |
| `test_intelligence.py` | `TestAdaptiveDifficulty`, `TestEngagementNudges`, `TestVisibilityControls` | Adaptive targets, nudge patterns, privacy filtering |
| `test_goal.py` | `TestGoal` | Goal state machine, completeness, remind delay |
| `test_goal_definition.py` | `TestGoalDefinition` | Domain and model validation on create/write |
| `test_security.py` | `TestSecurityRules`, `TestGroupMigration`, `TestAclParity` | ACL rows per tier, record-rule reach, group re-pointing |
| `test_menu_security.py` | `TestMenuSecurity` | Which menus each audience actually loads |
| `test_migrations.py` | `TestPostMigrate11` | The 1.1 rule/menu re-pointing script |
| `test_regressions.py` | `TestKarmaIntegrity`, `TestStreakTimezone`, `TestCronErrorIsolation`, `TestSkillTreeWiring`, `TestNudgeBudget`, `TestProfilePrivacy`, `TestGoalOutcomeFields`, `TestQuestOwnership`, `TestChallengeRetargeting`, `TestConsolidationPreservesGain`, … | One class per audited defect; each was red before its fix |

### Data (`data/`)

| File | Content |
|------|---------|
| `gamification_badge_data.xml` | 4 default badges (Good Job, Problem Solver, Hidden, Brilliant) |
| `gamification_challenge_data.xml` | 2 onboarding challenges: "Complete your Profile" + "Setup your Company" |
| `gamification_karma_rank_data.xml` | 5 ranks (Newbie→Doctor) + root/admin karma |
| `gamification_kudos_data.xml` | 5 categories (Teamwork, Innovation, Quality, Speed, Mentorship) |
| `mail_template_data.xml` | 4 email templates: badge received, goal reminder, challenge report, new rank reached |
| `ir_cron_data.xml` | 8 scheduled actions |

### Static (`static/src/`)

| File | Purpose |
|------|---------|
| `dashboard/gamification_dashboard.js` | OWL dashboard component (profile, leaderboard, feed, analytics) |
| `dashboard/gamification_dashboard.xml` | Dashboard template with 8 sections |
| `dashboard/gamification_dashboard.scss` | Dashboard styling |
| `notifications/gamification_notification_service.js` | Real-time bus notification handler |
| `scss/gamification.scss` | General gamification styles |

## Reading Order

1. **models.md** — All 28 models, fields, relationships, state machines
2. **architecture.md** — Subsystem interactions, execution flows, cron pipeline
3. **conventions.md** — Coding patterns, gotchas, safe_eval usage, test tags

## Related Modules

No enterprise or custom modules extend gamification in this codebase.
Extension points for other modules:
- Create `gamification.goal.definition` records for new measurable objectives
- Create `gamification.streak.type` records for activity-based streaks
- Create `gamification.achievement` records for hidden discovery achievements
- Create `gamification.quest` records for guided onboarding journeys
- Extend `_selection_origin_models()` to add new karma source models
- Override `prepare_rank_email_links()` for rank-reached email buttons

## Not wired

`gamification.quest.step` carries `definition_id` and `target_goal`, described
as "the goal definition this step evaluates". Nothing evaluates them: there is
no cron, no view button and no hook from `gamification.goal` back to a step.
Steps are completed only by calling `complete_step` from Python. Wiring them
means deciding whether a step is backed by a real `gamification.goal`, which is
a product decision — treat the two fields as unimplemented, not as a contract.
