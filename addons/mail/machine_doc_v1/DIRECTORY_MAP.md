# Directory Map

Maps each `static/src/` directory of the `mail` module → its **layer** (deployment context,
see `ASSET_LAYERS.md`) + primary responsibility. JS file counts are per-directory
(non-recursive), excluding `@types/`.

> Layer suffixes: `common` (everywhere incl. public page) · `web` (backend) · `public_web`
> (backend + public page) · `web_portal` (portal + backend) · `public` (public page only).
> See `ASSET_LAYERS.md` for how the suffix decides bundle membership.

## Top-level split

| Subtree | JS files | What |
|---------|---------:|------|
| `model/` | 10 | The client-side reactive ORM (`Record`/`Store`) — see `STATE_MANAGEMENT.md` |
| `core/` | 158 | The messaging framework: store service, models, base UI components |
| `discuss/` | 146 | The Discuss app feature layers (channels, calls, typing, voice, gifs, pinning) |
| `chatter/` | 13 | Form/portal document chatter |
| `views/` | 61 | Backend view integrations (activity view, mail field widgets, rotting widgets) |
| `utils/` | 12 | Shared date/format/DOM helpers |
| `webclient/` | 1 | Webclient-level wiring |
| `worklets/` | 1 | `audio_processor.js` — the RTC audio worklet, served raw by `/mail/rtc/audio_worklet_processor_v2` (not bundled) |
| `(root)` | 2 | `service_worker.js` + `service_worker_utils.js` |

The rows above sum to **404**, the module's full `static/src` JS count. (`audio/`, `img/`
and `scss/` carry no JS.)

> **`js/` no longer exists.** It was the last unlayered directory in the module — outside the
> `common`/`web`/`public_web`/`web_portal`/`public` scheme that decides bundling — and was
> retired in `9437c1915df`. Its contents moved to where their layer is legible:
> `js/rotting_mixin/` → `views/web/rotting/`, `js/tours/` → `discuss/core/web/tours/`,
> `js/onchange_on_keydown.js` → `views/web/fields/`, `js/emojis_mixin.js` → `utils/web/`, and
> `js/tools/` (the debug-menu item) → `views/web/debug_manager.js`. **An import of
> `@mail/js/…` resolves to nothing.**

## `model/` — the reactive ORM (layer: bundled everywhere)

| Directory | Files | Responsibility |
|-----------|------:|----------------|
| `model/` | 10 | `Record`, `Store`, `RecordList`, `RecordUses`, the `*_internal` engines, `make_store`, `misc` (registry + `fields` factory). See `STATE_MANAGEMENT.md` |

## `core/` — messaging framework

| Directory | Layer | Files | Responsibility |
|-----------|-------|------:|----------------|
| `core/common/` | common | 95 | Store service, the 31 core JS models (Thread, Message, Attachment, Composer, Follower, Notification, Activity, MessagingMenu, personas…) — 32 `.register()` calls counting the `Store` singleton itself — base components (composer, message, thread, chat window/hub, attachment views), core services |
| `core/common/plugin/` | common | 3 | html_editor plugins for the composer |
| `core/public_web/` | public_web | 13 | `DiscussClientAction`, the `Discuss` app UI, the `MessagingMenu` *component*, `DiscussApp` model — shared by backend + public page |
| `core/web/` | web | 41 | Backend-only: activity UI (menu, list popover, mark-as-done), follower list, backend chatter wiring, command palette, systray patches |
| `core/web_portal/` | web_portal | 1 | Portal+backend shared core |

## `discuss/` — the Discuss app

| Directory | Layer | Files | Responsibility |
|-----------|-------|------:|----------------|
| `discuss/core/common/` | common | 23 | Channel model patches, `discuss.core.common` service (channel bus subscriptions), sub-channels, member list |
| `discuss/core/public/` | public | 7 | Public-page boot (`boot.js`), welcome screen, public-only patches |
| `discuss/core/public_web/` | public_web | 19 | Sidebar, channel categories, `discuss.core.public.web` service, bus connection alert |
| `discuss/core/web/` | web | 12 | Backend Discuss integration, `discuss.core.web` service |
| `discuss/core/web/tours/` | web | 1 | The backend discuss tour (arrived from the retired `js/tours/`) |
| `discuss/call/common/` | common | 44 | The RTC engine: `discuss.rtc` service, P2P layer, call invitations, PiP, push-to-talk, `RtcSession` model, call UI |
| `discuss/call/public/` | public | 2 | Public-page call bootstrapping |
| `discuss/call/public_web/` | public_web | 5 | Shared call UI |
| `discuss/call/web/` | web | 3 | Backend call integration |
| `discuss/typing/common/` | common | 5 | "X is typing…" indicator + service |
| `discuss/voice_message/common/` | common | 11 | Voice-message recording/playback service, `VoiceMetadata` model |
| `discuss/voice_message/worklets/` | — | 1 | Audio worklet processor (served as raw JS) |
| `discuss/message_pin/common/` | common | 7 | Message pinning |
| `discuss/gif_picker/common/` | common | 4 | Tenor GIF picker |
| `discuss/web/` | web | 1 | Backend-only discuss glue |
| `discuss/web/avatar_card/` | web | 1 | Avatar hover-card popover |

## `chatter/` — document chatter

| Directory | Layer | Files | Responsibility |
|-----------|-------|------:|----------------|
| `chatter/web/` | web | 10 | Backend chatter: scheduled-message model, chatter container patches |
| `chatter/web_portal/` | web_portal | 3 | The `Chatter` component (form-view + portal) — shipped standalone as `mail.assets_chatter_web_portal` |

## `views/` — backend view integrations (layer: web)

**Everything under `views/` is in the `web` layer** — the whole subtree is `views/web/…`;
there is no unlayered `views/fields/`. Unlike the tables above, these rows are **recursive**
(each widget lives in its own subdirectory); they sum to the subtree's 61 files.

| Directory | Files | Responsibility |
|-----------|------:|----------------|
| `views/web/` (root) | 2 | `debug_manager.js` (debug-menu items) + view-registry glue |
| `views/web/activity/` | 8 | The Activity view type (calendar-like activity board) |
| `views/web/calendar/` (+ `calendar_common`, `calendar_year`) | 6 | Calendar-view mail integration |
| `views/web/fields/` | 29 | Mail field widgets: avatar + avatar-autocomplete, `many2one_avatar_user`, `many2many_avatar_user`, `many2many_tags_email`, emojis char/text/common, `shortcut_char`, html-composer/mail fields, kanban/list activity, scheduled-date, activity-exception, activity-model-selector, badge-selection-icons, mail-server-configurator, statusbar-duration, properties, `onchange_on_keydown` |
| `views/web/rotting/` | 9 | "Rotting" kanban/statusbar widgets (stale-record highlighting) driven by `mixin.mail.tracking.duration` — arrived from the retired `js/rotting_mixin/` |
| `views/web/kanban/`, `views/web/list/`, `views/web/model/`, `views/web/view_dialog/` | 7 | Kanban/list activity columns, model helpers, view dialogs |

## `utils/` , `webclient/`

| Directory | Layer | Files | Responsibility |
|-----------|-------|------:|----------------|
| `utils/common/` | common | 9 | `format.js`, `dates.js`, `hooks.js`, `misc.js`, `counters.js`, `media_monitoring.js`, `pdf_thumbnail.js`, `composer_insert.js`, `thread_read.js` |
| `utils/web/` | web | 1 | `emojis_mixin.js` — backend-only, so it cannot sit in `utils/common/`, which ships on the public page |
| `webclient/web/` | web | 1 | Webclient-level mail wiring |

> `utils/common/format.js` is the one mail file in `web.assets_frontend`; that is why the
> split matters. Adding a backend-only helper to `utils/common/` would ship it to every
> frontend page — put it in `utils/web/`.

## `scss/` (styles only, no JS)

| Directory | What |
|-----------|------|
| `scss/` | Shared mail SCSS (variables, base styles) |
| `scss/variables/` | `primary_variables.scss` (→ `web._assets_primary_variables`) + `derived_variables.scss` |

> Component SCSS is **co-located** with its `.js`/`.xml` trio (e.g.
> `core/common/composer.{js,xml,scss}`), following the same OWL-trio convention as
> the web module. There are no `*.dark.scss` files left in mail: `web` now answers
> both colour schemes from one stylesheet (see `ASSET_LAYERS.md`).

## Non-JS directories (module root)

| Directory | What |
|-----------|------|
| `models/` (+ `models/discuss/`) | 82 Python model files (68 + 14) — see `MODEL_MAP.md` |
| `controllers/` (+ `controllers/discuss/`) | 20 controller files, 64 routes — see `ROUTE_MAP.md` |
| `wizards/` | 9 wizard `.py` files (composer, activity schedule + summary, blacklist remove, followers edit, template preview/reset, + 2 `_inherit` hooks) |
| `tools/` | Pure-Python helpers: `discuss.py` (guest context + `Store`), `access_scan.py`, `alias_error.py`, `channel_avatar.py`, `jwt.py`, `link_preview.py`, `mail_validation.py`, `parser.py`, `web_push.py` |
| `data/` | 15 XML data files (subtypes, activity types, templates, channels, crons) |
| `demo/` | 4 demo XML files |
| `views/` | 41 backend view XML files |
| `security/` | `ir.model.access.csv` + `mail_security.xml` |
| `migrations/` | `19.0.1.20/post-migration.py`, `19.0.1.21/pre-migration.py` |
| `static/lib/` | Vendored libs: idb-keyval, lame, odoo_sfu, selfie_segmentation (see `ASSET_LAYERS.md`) |
| `static/tests/` | 143 HOOT `*.test.js` + helpers + tours — see `TEST_TAGS.md` |
| `push-to-talk-extension/` | Browser extension source for the push-to-talk feature |
