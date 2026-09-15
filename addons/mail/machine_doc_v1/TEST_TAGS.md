# Mail Module Test Tags

Reference for running targeted subsets of the `mail` module's tests — Python
(`tests/`, 71 `test_*.py` files) and JavaScript HOOT (`static/tests/`, 156 `*.test.js`).

> **See also**: `CONVENTIONS.md` (the mock-gateway / bus test helpers), `ROUTE_MAP.md`
> (the controller-contract tests), `STATE_MANAGEMENT.md` (what the JS store tests exercise).

## Python — how mail tests are tagged

Almost every mail test class is decorated `@tagged("post_install", "-at_install", …)` — the
suites need a fully-installed database (mail wires into `res.partner`, `res.users`, the bus,
etc.). Of **141** tagged classes, **112** carry `post_install`/`-at_install`. Note both
decorator spellings are in use (`@tagged(...)` and `@odoo.tests.tagged(...)`, the latter in
e.g. `test_js.py` and `discuss/test_discuss_attachment_controller.py`) — grep for both or you
will undercount. Topic tags on top of that are
**sparse** — many files carry only the install-phase tags and are selected by the module
filter (`-u mail`) alone, not by a topic tag.

### Topic tags → files

Class counts measured 2026-08-17 at `dd172d10485`; `factcheck.sh` pins them.

| Tag | Classes | Files | Covers |
|-----|--------:|-------|--------|
| `mail_controller` | 7 | `test_mock_server_contract.py`, `discuss/test_*_controller.py` (message, reaction, binary, message_update, thread, attachment) | HTTP controller ↔ store-payload contract |
| `mail_template` | 6 | `test_mail_template.py` | `mail.template` + `send_mail` |
| `mail_tools` | 5 | `test_mail_tools.py`, `test_res_partner.py`, `test_res_users.py` | Email parsing/normalization helpers |
| `mail_composer` | 4 | `test_mail_composer.py` | `mail.compose.message` wizard |
| `mail_message` | 4 | `test_mail_message.py`, `test_mail_message_translate.py`, `test_link_preview.py`, `discuss/test_message_controller.py` | `mail.message` model + translation |
| `mail_render` | 3 | `test_mail_render.py` | QWeb / inline-template rendering |
| `res_users` | 3 | `test_res_users.py` | User mail behavior |
| `mail_activity` | 2 | `test_mail_activity.py` | `mail.activity` scheduling/state |
| `mail_server` | 2 | `test_ir_mail_server.py` | Outgoing SMTP server selection/config |
| `mail_js` | 2 | `test_js.py` | Runs the JS/HOOT suites in a headless browser |
| `res_partner` | 2 | `test_res_partner.py`, `test_mail_tools.py` | Partner mail behavior |
| `regex_render` | 1 | `test_mail_render.py` | The restricted ("static") render path — see CONVENTIONS.md gotcha 8. The tag name predates the regex's removal |
| `mail_asset_index` | 1 | `test_mail_asset_index.py` | `core/common/_models.js` lists exactly the `*_model.js` files beside it, in both directions, and each indexed file registers. Reads the tree, needs no database or bundle |
| `mail_store_contract` | 1 | `test_mock_server_contract.py` | The JS-store ↔ server payload shape contract |
| `mail_link_preview` | 1 | `test_link_preview.py` | URL link-preview generation |
| `mail_init` | 1 | `test_mail_tools.py` | Module init / post-init hook |
| `mail_thread` | 1 | `test_ir_ui_menu.py` | `mixin.mail.thread` integration |
| `mail_thread_api` | 1 | `test_res_partner.py` | `mixin.mail.thread` public API |
| `discuss_action` | 1 | `discuss/test_discuss_action.py` | Discuss client-action loading |
| `RTC` | 1 | `discuss/test_rtc.py` | WebRTC call session model |
| `is_tour` | 1 | `discuss/test_discuss_channel_as_guest.py` | Guest browser tours |
| `mail_notification` | 1 | `test_mail_notification.py` | `format_failure_reason`, in the recipient's language |
| `web_manifest` | 1 | `test_webmanifest.py` | Service worker + web manifest served to the browser |

**40 of the 71 test files carry no topic tag at all** and are reachable only by the module
filter — among them `test_fetchmail.py`, `test_mail_mail.py`, `test_mail_blacklist.py`,
`test_mail_message_access_parity.py`, `test_mail_message_search.py`, `test_uninstall.py`,
`test_update_notification.py`, and **18 of the 28 files** in `discuss/`. That is **more than
half the module**: a `--test-tags` run covers 24 files, so treat the tag table as a way to
go fast, never as a way to say "mail passed". Use `-u mail --test-enable` for that.

> **The round-numbered hardening suites are gone.** `test_mail_hardening_v2` … `_v13` and
> `test_mail_audit_v6*` — twenty-one files, eight of them carrying dedicated
> `mail_hardening_v*` tags — were deleted in `e4df7f5569b`. Those tags now select nothing, so
> a run using one reports success having executed no test. What survived is
> `test_mail_message_access_parity.py`, which pins the access rule's two spellings against
> each other rather than restating one audit round's findings. New regression tests go in the
> suite named after what they test — see CONVENTIONS.md gotcha 9.

### Base test classes (`tests/common.py`)

The mail test tower — subclass `MailCommon` for almost everything:

| Class | Extends | Provides |
|-------|---------|----------|
| `MockEmail` | `BaseCase`, `MockSmtplibCase` | SMTP mocking foundation. `mock_mail_gateway(mail_unlink_sent=False)` ctx mgr (wraps `mail.mail` create/unlink), `mock_push_to_end_point`, `mock_datetime_and_now`. Assertions: `assertMailMail`, `assertMailMailWEmails/WRecord/WId`, `assertMessageFields`, `assertNoMail`, `assertSentEmail`/`assertNotSentEmail`, `assertPushNotification`/`assertNoPushNotification`, `assertTracking`, `assertHtmlEqual` |
| `MailCase` | `TransactionCase`, `MockEmail`, `BusCase` | Adds bus mocking (`mock_bus`), `mock_mail_app` (mocks `mail.message`/`mail.notification` create), `_reset_mail_context`. Assertions: `assertSinglePostNotifications`, `assertPostNotifications`, `assertBus`, `assertMailNotifications`, `assertBusNotifications`, `assertBusNotificationType`, `assertNotified`, `assertNoNotifications` |
| `MailCommon` | `MailCase` | Highest-level base; `setUpClass` provisions users / partners / templates. **The class most tests subclass.** |

Downstream bases: `MailControllerCommon(HttpCase, MailCommon)` and its children
(`MailControllerAttachmentCommon`, `MailControllerBinaryCommon`,
`MailControllerReactionCommon`, `MailControllerThreadCommon`, `MailControllerUpdateCommon`)
for controller-contract tests; `TestMailRenderCommon` for rendering; `MailTrackingDurationMixinCase`.

> The primary hooks are `mock_mail_gateway` (capture outgoing mail without SMTP),
> `mock_bus` (capture bus notifications), and `assertMailMail` (assert an outgoing
> `mail.mail`).

### Running Python tests

From the **workspace root** (`~/Odoo`), whose paths these are — see workspace CLAUDE.md §2.

```bash
PY="p314o19m/bin/python odoo/odoo-bin"
CONF=p314o19m.conf

# Controller ↔ store contract:
$PY -c $CONF -d <db> --test-tags mail_controller --stop-after-init --no-http

# A single class/method:
$PY -c $CONF -d <db> --test-tags '/mail:TestMailActivity.test_activity_flow' --stop-after-init --no-http

# All mail tests (module filter; the only way to reach the 28 topic-tag-less files):
$PY -c $CONF -d <db> -u mail --test-enable --stop-after-init --no-http
```

> **`p314o19m.conf` puts `enterprise/` on the addons path**, which pulls in ~40 modules of
> auto-installs that patch mail. For anything you intend to compare against CI, use the CI
> scope instead — from the `odoo/` checkout root, `--addons-path=odoo/addons,addons`, which
> installs 27 modules.

### ⚠ The query-count suite is red before you start

This suite is in the **sibling `test_mail` module**, not in `mail`.
`test_mail/tests/test_performance.py` (tag `mail_performance`) pins exact query
counts with `assertQueryCount`, and it is red before you touch anything.

**Measured 2026-08-17 at `dd172d10485`, CI scope (27 modules): 56 failed, 0
errors of 72 tests.** Underneath that headline, in `test_performance.py`:

| | |
|---|---:|
| failing `assertQueryCount` blocks | **63** |
| — over the floor | 56 (**334** surplus queries) |
| — under the floor | 7 (**9** queries below) |
| distinct failing tests | 36 (30 over, 6 under) |

```bash
# from the workspace root; the CI addons-path, per odoo/CLAUDE.md
p314o19m/bin/python odoo/odoo-bin --addons-path=odoo/odoo/addons,odoo/addons \
    -d <ci-db> -i mail,test_mail --test-enable --test-tags mail_performance \
    --stop-after-init --no-http
```

One more block fails outside that file — `test_mail_template.py:434`
`test_template_send_email_wreport_batch`, 149 **<** 240, a floor the batching
work has already overtaken by 91 queries.

⚠ **Symlink `node_modules` into the checkout you measure in**, or the two
`*_wreport*` tests error on `EsbuildBundleError` instead of reporting a count,
and you will read 2 errors that are about your toolchain (workspace CLAUDE.md §4).

Two separate things inflate the numbers, so check both before believing one:

1. **Your database's module set.** A DB built with the workspace conf installs
   ~40 modules, because `enterprise/` is on the `addons_path` and pulls in
   auto-installs (`ai_fields`, `snailmail`, `mail_mobile`, `auth_totp_mail`,
   …), each adding `write`/`create` overrides. Harvest and compare at CI scope,
   as above.

2. **The floors themselves have drifted** (e.g. 48 vs 34, 108 vs 94). Fixing that
   is a per-test judgement — is this delta legitimate or a real regression? —
   *not* a blanket re-baseline, which would cement whatever regressions are
   hiding in it.

   The analysis below was done in an earlier pass, at a different commit; the
   *causes* it names still hold and the arithmetic in it is that pass's, not the
   measurement above. Where it quotes a total, treat it as the shape of the drift
   rather than today's number.

   | Cause | Share of the 283 surplus queries |
   |-------|-------|
   | `mail.followers` savepoint guard (below) | 52 (~18%), present in 25 assertions, the whole surplus in 6 |
   | ORM record-rule access check (below) | 20 (~11%), fully explains 6 tests |
   | still unattributed | the rest — concentrated in `message_post` / `_notify_thread` |

   So there is **no single cause** — do not assume one. Two are identified and
   both are *legitimate cost*, i.e. the floors are stale rather than the code
   being wrong:

   **The follower savepoint — paid off.** `mail.followers._create_followers`
   used to wrap its `create` in `cr.savepoint(flush=False)` and retry row-by-row
   on `IntegrityError`, because two transactions auto-subscribing the same
   partner race the `unique(res_model, res_id, partner_id)` index. `SAVEPOINT` +
   `RELEASE` are two real queries, so **any test that auto-subscribes a follower
   paid +2** — the entire delta for `test_create_mail_simple`,
   `test_create_mail_simple_multi`, `test_create_mail_with_tracking` and
   `test_adv_activity`, then all 10/8-shaped.

   The race protection was not removed, it was **replaced**: one
   `INSERT ... ON CONFLICT DO NOTHING RETURNING`, where a row that does not come
   back is a raced pair reported to the caller. No savepoint, no `O(N)` retry,
   and no `odoo.db.cursor` warning claiming a handled conflict was "surfaced to
   the user". Measured over `/test_mail,/test_mail_sms`: **44 query-count blocks
   fell, net −160 queries, none rose**, and those four are back at 8/8/9/8. If
   you are here because a follower count moved *up*, the savepoint is not the
   explanation any more — look at `_create_followers` itself.

   The access-check share is
   real but small: since `a7450df423d [IMP] core: checking/testing/filtering
   access on records`, record rules are evaluated **in Python against the
   records** (`write -> check_access -> _check_access -> filtered_domain`) rather
   than folded into SQL, so a non-superuser write fetches whatever field the rule
   names when it is not already cached. `TestBaseMailPerformance.test_write_mail_simple`
   (2 > 1) is exactly and only that, and is **not** a mail defect.

   **The residual is diffuse, and that is a measured result, not a shrug.**
   Attributing every query in the `message_post` tests to its own call site
   (deepest `/addons/` frame, with line numbers) gives ~25 distinct sites each
   contributing exactly one query — `_message_compute_parent_id`,
   `_notify_get_reply_to_batch`, `_get_forbidden_access`,
   `_get_accessible_documents`, `_add_default_followers`,
   `_get_subscription_data`, `_get_recipient_data`, `_compute_main_user_id`,
   `_notify_by_email_prepare_rendering_context`, `_split_by_mail_configuration`,
   `_prepare_outgoing_list`, `_postprocess_sent_message`, and so on. No third
   systematic cause exists to find: these floors have to be re-judged
   test-by-test, asking of each added query whether it belongs to a fork feature
   that was meant to cost it.

   Ranked by size, for whoever starts: `test_mail_composer_mass_w_template` +21,
   `test_message_post_template` +11/+10, `test_message_post_view` +11,
   `test_mail_mail_send_batch_complete` +10, `test_message_post_followers` +7/+6.

   Two things that look like causes but are not. `base.py:36` (mail's `unlink`
   override on `base`) tops the per-caller counts, but line 36 is
   `result = super().unlink()` — those are the ORM's own deletes, attributed to
   the nearest addon frame. Mail's *own* cost there is the `mail.activity` search
   on line 45, and it is **one** query per `unlink()` call, batched over all the
   ids, not per record.

   **The drift runs both ways.** Of 68 failing assertions at CI scope, 57 are
   "more than expected" (283 surplus queries) but **11 are "less"** (19 queries
   below the floor) — floors that improvements have already overtaken (e.g.
   `test_mail_composer_w_template`, `test_partner_find_from_emails`, both -2).
   A blanket raise would be wrong in both directions at once.

**Ten floors are already re-set**, as the worked precedent for the rest. The bar
used, and to keep using: raise a floor only where the *entire* surplus of that
one `assertQueryCount` block is a named, understood cause.

- Savepoint pair (+2 each): `test_create_mail_simple`,
  `test_create_mail_simple_multi`, `test_create_mail_with_tracking`,
  `test_adv_activity`.
- Access check (+1 or +2): `test_write_mail_simple`,
  `test_message_log_with_post`, `test_message_post_no_notification`,
  `test_message_get_suggested_recipients`, and *one block each* of
  `test_message_subscribe_subtypes` and `test_message_subscribe_default`.

- Both together: the remaining blocks of `test_message_subscribe_subtypes`,
  `test_message_subscribe_default`, and all three blocks of
  `test_message_subscribe` (savepoint +2, sometimes plus one access-check fetch).

**The 19 "less than expected" floors are also done, and they needed no cause
analysis at all.** A floor the code has already outrun can be lowered to the
measured value safely: a *lower* floor cannot hide a regression, it only tightens
future detection. Each mapped to a unique block, so all 11 tests were updated
mechanically — `test_activity_full`, `test_activity_mixin`(+`_w_attachments`),
the five `test_mail_composer_*` variants, `test_partner_find_from_emails`, and
`test_message_get_default_recipients`(+`_batch`). Do these first in any future
pass: they are free.

Verified at CI scope at the time: **"less than expected" 19 -> 0**, failing tests
**48 -> 34**, with **nothing newly failing** at any step. (Odoo's headline
"65 failed" barely moves across the last step, because most of those tests have a
second block still failing for an unrelated reason — count blocks, not tests,
when judging progress.)

> **Re-measured 2026-08-17: those ten raises have held.** Every test named above
> is clean at `dd172d10485` — none has drifted back over its new floor. But
> **"less than expected" is back to 7 blocks / 6 tests**, two of them tests this
> pass raised (`test_message_get_suggested_recipients` 24 < 25,
> `test_message_get_default_recipients` 4 < 5) and now overtaken *again* by later
> improvements, plus `test_activity_full` (×2), the two `test_message_to_store_*`
> and `test_message_get_suggested_recipients_batch`. That is the "drift runs both
> ways" point restated by the tree itself: **under-floor blocks reappear
> continuously**, so lowering them is not a one-off chore but the cheap half of
> every pass.

Two traps this exercise hit, both worth avoiding:

- **Fix blocks, not tests.** A test with several `assertQueryCount` blocks can
  have several failing for different reasons. `test_message_subscribe_subtypes`
  had one block explained purely by the access check and another needing the
  savepoint too.
- **Never `sort -u` the failure list while mapping blocks.** Two blocks of
  `test_message_subscribe` both expected 4 and both got 6, so dedup collapsed
  them into one line and hid the third failing block. It only surfaced after the
  first two were fixed.

One raise is independently corroborated: the access-check analysis put
`test_message_get_suggested_recipients` at 25 (from 23), and the pristine
upstream floor for that block is **also 25** — two unrelated routes agreeing on
the same number. Our 23 had simply been set too low.

**A shortcut that does not work, so you need not retry it.** The pristine
upstream `19.0` mirror carries this same file, so it is tempting to adopt its
floors wholesale. Measured in that pass, not re-verified since: of the 64 then-remaining failing assertions, **zero** have
an actual count equal to upstream's floor for the same block. The remaining drift
is genuinely fork-specific behaviour, not our copy of the floors having gone
stale against upstream — which is precisely why the rest needs per-query
judgement rather than a diff. (Worth knowing anyway: 24 blocks already differ
from upstream, and before this pass a handful of ours sat *below* it.)

**To tell whether *your* change moved a count**, diff the numbers rather than the
pass/fail, since the tests fail either way:

```bash
odoo-bin --addons-path=odoo/addons,addons -d <ci-db> --test-enable \
    --test-tags mail_performance --stop-after-init --no-http 2>&1 \
  | grep -oE "for user [a-z]+: [0-9]+ [<>] [0-9]+ in [a-z_0-9]+ at [^ ]+" \
  | LC_ALL=C sort > after.txt
# ...then the same with your change reverted, and `diff before.txt after.txt`.
```

Three things that pattern gets right and the obvious one does not: `[<>]` keeps
the **under**-floor blocks (a change that *lowers* a count moves those and
nothing else); `[a-z_0-9]+` matches test names ending in a digit
(`..._v2`, `..._128`), which `[a-z_]+` silently truncates into a wrong key; and
keeping ` at <file>:<line>` makes the block, not the test, the unit — two blocks
of one test can move in opposite directions, and without the line number `sort`
merges them.

`assertQueryCount` reports only the count, never the queries. To see *which*
queries, wrap `self.cr.execute` for the duration of the block — the useful frame
is the last one under `/addons/`, since everything below it is ORM.

## JavaScript — HOOT suites (`static/tests/`)

154 `*.test.js` files. They run in a headless browser via `test_js.py` (tag `mail_js`), or
interactively at `/web/tests` (mail is included in `web.assets_unit_tests`).

### File groups (by subdirectory)

Rows below sum to 156.

| Directory | Files | Scope |
|-----------|------:|-------|
| `discuss/` | 46 | Discuss app: channels, members, calls, sidebar, sub-channels |
| `core/` | 30 | Store/Record framework, personas, notifications, settings, presence, the localStorage mirror |
| `web/` | 9 | Backend-web integration (systray, form chatter wiring) |
| `chatter/` | 10 | Form-view chatter |
| `discuss_app/` | 6 | Discuss client-action shell |
| `utils/` | 6 | Date/format/misc helper units |
| `composer/` | 5 | Message composer |
| `thread/` | 6 | Thread rendering + message list |
| `(root)` | 9 | Cross-cutting suites + helpers |
| `message/` | 4 | Message component |
| `activity/` | 3 | Activities |
| `chat_window/`, `emoji/`, `inline/`, `messaging_menu/`, `views/` | 2 each | — |
| `chat_bubble/`, `crosstab/`, `gif_picker/`, `html_editor/`, `messaging/`, `mobile/`, `quick_reaction_menu/`, `scheduled_message/`, `suggestion/`, `translation/`, `widgets/` | 1 each | — |
| `mock_server/` | 0 | Mock-server models and route contracts — harness, not suites |
| `tours/` | 0 | Browser tours — excluded from the unit bundle (ship in `web.assets_tests`) |

### JS test helpers

`static/tests/mail_test_helpers.js` is the central harness:

| Export | Role |
|--------|------|
| `defineMailModels()` | `defineModels(mailModels)` — installs all mock models for a suite |
| `mailModels` | Registry of the mock model set |
| `start(options)` | Boot a mail-enabled test env |
| `startServer()` | Create the mock server |
| `openDiscuss(activeId, {target})` | Mount the Discuss app on a channel/mailbox |
| `openFormView` / `openKanbanView` / `openListView` / `openView` | Mount a backend view with chatter |
| `onRpcBefore` / `onRpcAfter`, `registerArchs`, `patchUiSize` | RPC hooks / arches / responsive sizing |
| `listenStoreFetch` / `waitStoreFetch`, `STORE_FETCH_ROUTES = ["/mail/action","/mail/data"]` | Await the batched store fetches |
| `makeMockRtcNetwork`, `createVideoStream`, `mockGetMedia`, `patchBrowserNotification` | RTC / media / notification mocks |
| `setupChatHub` / `assertChatHub`, `prepareRegistriesWithCleanup`, `userContext` | Chat-hub + registry helpers |

Other helper files: `mail_test_helpers_contains.js` (DOM `contains`-style assertions),
`mail_shared_tests.js` (reusable test bodies),
`mock_server/mail_mock_server.js` (41 mocked RPC routes, all via `registerRoute("<path>", …)`),
`mock_server/mock_models/` (35 mock model files: `mail_thread.js`, `mail_message.js`,
`discuss_channel.js`, `discuss_channel_member.js`, `discuss_channel_rtc_session.js`,
`mail_activity.js`, `res_partner.js`, `mail_guest.js`, `mail_notification.js`,
`ir_websocket.js`, …).

### Running JS tests

```bash
# Full HOOT suite in a headless browser (slow):
$PY -c $CONF -d <db> --test-tags mail_js --stop-after-init

# Interactively: start the server and open
#   http://localhost:8069/web/tests  → filter to @mail suites
```

> **Scoped bundle.** `_run_hoot` appends `&module_scope=mail`, so these runs load
> only mail's manifest dependency closure (`mail`, `web_tour`, `html_editor`,
> `bus`, `web`, `base`) instead of every installed addon's `src`. Enterprise
> addons that patch mail (`ai`, `mail_mobile`, `mail_bot`, `sms`, …) are
> absent, which is why `@mail` suites no longer log `[ai] CommandPalette:
> ai.agent unavailable`. Opening `/web/tests` by hand has no scope and still
> loads everything — expect that noise back. See `web/machine_doc_v1/TEST_TAGS.md`
> § "HOOT suite scoping".
