# Mail Module Route Map

Complete mapping of HTTP endpoints to Python handlers for the `mail` module
(`addons/mail/controllers/`, including `controllers/discuss/`).

> **See also**: `ARCHITECTURE.md` (request flow, the `/mail/data` ↔ `/mail/action`
> split), `STATE_MANAGEMENT.md` (how batched fetches feed the JS Store),
> `CONVENTIONS.md` (the guest-context auth flow).

Legend: `jsonrpc` = POST JSON-RPC 2.0 · `http` = standard HTTP · `+guest` = the
`@add_guest_to_context` decorator populates `context["guest"]` from the `dgid` cookie
(see **Guest auth** below) · `auth` = Werkzeug auth type · `readonly` = routed to a read
replica if configured.

**Route defaults when omitted** — `auth="user"`, `csrf` enabled for `http` (disabled for
`jsonrpc`), and `readonly` **defaults to `auth == "none"`**, *not* to `False`:

```python
# odoo/http/routing.py — _prepare_route_fragment
default_mode = fragment.get("readonly", default_auth == "none")
```

So mail's one `auth="none"` handler (`export_icon_to_png`, 20 URLs) is **readonly at
runtime** despite never declaring it — verified against the live routing map, where all 20
report `readonly=True`. Every other mail route's runtime `readonly` matches its source
declaration exactly.

**Total: 64 `@http.route` handlers** — 31 in `controllers/`, 33 in `controllers/discuss/` —
across **84 URL strings** (20 of them `export_icon_to_png`'s font_to_img variants).

## The two central data endpoints

Almost all backend data flows through **two batched endpoints** on
`WebclientController` (`controllers/webclient.py`), both `auth="public"` + `+guest`:

| Route | Type | Readonly | Handler | Purpose |
|-------|------|----------|---------|---------|
| `/mail/data` | jsonrpc | **yes** | `mail_data` | Batched **read-only** data fetch → `store.insert(...)` |
| `/mail/action` | jsonrpc | no | `mail_action` | Batched data fetch **with side effects** |

The JS Store's `_fetchStoreDataRpc` picks `/mail/data` when the batch is read-only,
`/mail/action` otherwise (`store_service.js`). Named fetch *params* (`init_messaging`,
`channels_as_member`, `discuss.channel`, `/discuss/get_or_create_chat`,
`/discuss/create_channel`, `/discuss/create_group`, …) are dispatched **inside** these two
routes by `DiscussChannelWebclientController._process_request_*` — they are **not**
standalone routes.

## Messaging core (`controllers/`)

### controllers/thread.py — `ThreadController`
Base class for several controllers below (`AttachmentController`, `MessageReactionController`,
`WebclientController` subclass it). Module helpers `_to_record_id`/`_to_record_ids` are not routes.

| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/message/post` | jsonrpc | public +guest | `mail_message_post` | Post a message on a thread |
| `/mail/message/update_content` | jsonrpc | public +guest | `mail_message_update_content` | Edit message body / attachments |
| `/mail/thread/messages` | jsonrpc | user | `mail_thread_messages` | Fetch a thread's messages |
| `/mail/thread/recipients` | jsonrpc | user | `mail_thread_recipients` | Suggested recipients for a thread |
| `/mail/thread/recipients/get_suggested_recipients` | jsonrpc | user | `mail_thread_recipients_get_suggested_recipients` | Recompute suggested recipients with frontend edits |
| `/mail/thread/subscribe` | jsonrpc | user | `mail_thread_subscribe` | Subscribe partners to a record |
| `/mail/thread/unsubscribe` | jsonrpc | user | `mail_thread_unsubscribe` | Unsubscribe partners from a record |
| `/mail/partner/from_email` | jsonrpc | user | `mail_thread_partner_from_email` | Find/create partners from emails |
| `/mail/read_subscription_data` | jsonrpc | user | `read_subscription_data` | Subtypes + followed subtypes for a follower |

### controllers/mailbox.py — `MailboxController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/inbox/messages` | jsonrpc | user (readonly) | `discuss_inbox_messages` | Inbox (needaction) messages |
| `/mail/history/messages` | jsonrpc | user (readonly) | `discuss_history_messages` | History (non-needaction) messages |
| `/mail/starred/messages` | jsonrpc | user (readonly) | `discuss_starred_messages` | Starred messages |

### controllers/attachment.py — `AttachmentController(ThreadController)`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/attachment/upload` | http | public +guest, POST | `mail_attachment_upload` | Upload onto a thread / pending compose |
| `/mail/attachment/delete` | jsonrpc | public +guest | `mail_attachment_delete` | Delete an attachment (ownership-token gated) |
| `/mail/attachment/zip` | http | public +guest, POST | `mail_attachment_get_zip` | Stream a zip of comma-separated attachment ids |
| `/mail/attachment/pdf_first_page/<int:attachment_id>` | http | public +guest (readonly), GET | `mail_attachment_pdf_first_page` | First page of a PDF |
| `/mail/attachment/update_thumbnail` | jsonrpc | public +guest | `mail_attachment_update_thumbnail` | Set/replace PDF thumbnail |

### controllers/message_reaction.py — `MessageReactionController(ThreadController)`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/message/reaction` | jsonrpc | public +guest | `mail_message_reaction` | Add/remove an emoji reaction |

### controllers/link_preview.py — `LinkPreviewController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/link_preview` | jsonrpc | public +guest | `mail_link_preview` | Generate link previews for a message |
| `/mail/link_preview/hide` | jsonrpc | public +guest | `mail_link_preview_hide` | Hide a message's link previews |

### controllers/google_translate.py — `GoogleTranslateController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/message/translate` | jsonrpc | user | `translate` | Translate a message body (rate-limited) |

### controllers/im_status.py — `ImStatusController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/set_manual_im_status` | jsonrpc | user, POST | `set_manual_im_status` | Set manual IM presence |

### controllers/guest.py — `GuestController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/guest/update_name` | jsonrpc | public +guest, POST | `mail_guest_update_name` | Rename a guest |

### controllers/mail.py — `MailController`
Notification-email redirect targets + the mass-mailing font-to-image renderer.

| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/view` | http | public | `mail_action_view` | Notification-email redirect → record / messaging / login |
| `/mail/unfollow` | http | public (csrf=False) | `mail_action_unfollow` | Unsubscribe a partner (MUA link, token-checked) |
| `/mail/message/<int:message_id>` | http | public +guest | `mail_thread_message_redirect` | Redirect to a message's record, highlighting it |
| `/web_editor/font_to_img/<icon>` … + `/mail/font_to_img/<icon>` … (20 URL variants: 10 per prefix) | http | none (**readonly**, implicitly — see legend) | `export_icon_to_png` | Render a font glyph to PNG (mass-mailing). Sets `Access-Control-Allow-Origin: *` manually in the body — not via the `cors=` kwarg |

### controllers/websocket.py — `WebsocketControllerPresence(WebsocketController)`
Extends `bus`'s websocket controller.

| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/websocket/peek_notifications` (inherited from `bus`; mail re-`@route()`s it with no URL) | jsonrpc | public +guest | `peek_notifications` | Override of bus poll to inject guest context |
| `/websocket/update_bus_presence` | jsonrpc | public (cors=`"*"`) | `update_bus_presence` | Update current bus presence |

### controllers/webmanifest.py — `WebManifest`
**0 routes.** Overrides `_get_service_worker_content` only — injects web-push code into the
service worker for internal users.

## Discuss (`controllers/discuss/`)

### controllers/discuss/channel.py — `ChannelController` + `DiscussChannelWebclientController`
`DiscussChannelWebclientController(WebclientController)` has **0 routes** — it overrides
`_process_request_loop` / `_process_request_for_all` to handle the `/mail/data` +
`/mail/action` fetch-params. `ChannelController(http.Controller)` holds the routes:

| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/discuss/channel/members` | jsonrpc | public +guest (readonly) | `discuss_channel_members` | Fetch unknown members + count |
| `/discuss/channel/messages` | jsonrpc | public +guest | `discuss_channel_messages` | Fetch channel messages |
| `/discuss/channel/pinned_messages` | jsonrpc | public +guest (readonly) | `discuss_channel_pins` | Fetch pinned messages |
| `/discuss/channel/mark_as_read` | jsonrpc | public +guest | `discuss_channel_mark_as_read` | Mark read up to a message |
| `/discuss/channel/set_new_message_separator` | jsonrpc | public +guest | `discuss_channel_set_new_message_separator` | Set the "new messages" separator |
| `/discuss/channel/notify_typing` | jsonrpc | public +guest | `discuss_channel_notify_typing` | Broadcast typing state |
| `/discuss/channel/attachments` | jsonrpc | public +guest (readonly) | `load_attachments` | Load channel attachments (paged) |
| `/discuss/channel/join` | jsonrpc | public +guest | `discuss_channel_join` | Join a channel |
| `/discuss/channel/update_avatar` | jsonrpc | **user** (default) | `discuss_channel_avatar_update` | Update channel `image_128` |
| `/discuss/channel/sub_channel/create` | jsonrpc | public +guest | `discuss_channel_sub_channel_create` | Create a sub-channel |
| `/discuss/channel/sub_channel/fetch` | jsonrpc | public +guest | `discuss_channel_sub_channel_fetch` | Fetch sub-channels (paged/search) |
| `/discuss/channel/sub_channel/delete` | jsonrpc | user | `discuss_delete_sub_channel` | Delete a sub-channel (creator only) |

> `/discuss/channel/update_avatar` has no explicit `auth=` → falls back to `http.route`'s
> `auth="user"` default. Two `channel.py` routes require login: `update_avatar` (implicit
> default) and `/discuss/channel/sub_channel/delete` (explicit `auth="user"`). All the other
> `channel.py` routes are `auth="public"` +guest.

### controllers/discuss/public_page.py — `PublicPageController`
The anonymous discuss public-page entry points (render the standalone Discuss app).

| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/chat/<string:create_token>` + `/chat/<string:create_token>/<string:channel_name>` | http | public +guest, GET | `discuss_channel_chat_from_token` | Open/create a token-based public chat |
| `/meet/<string:create_token>` + `/meet/<string:create_token>/<string:channel_name>` | http | public +guest, GET | `discuss_channel_meet_from_token` | Same, defaults to full-screen video |
| `/chat/<int:channel_id>/<string:invitation_token>` | http | public +guest, GET | `discuss_channel_invitation` | Join via invitation token |
| `/discuss/channel/<int:channel_id>` | http | public +guest, GET | `discuss_channel` | Render the public discuss channel page |

### controllers/discuss/rtc.py — `RtcController`
WebRTC call signaling and worklet serving.

| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/mail/rtc/session/notify_call_members` | jsonrpc | public +guest | `session_call_notify` | Relay P2P signaling between sessions |
| `/mail/rtc/session/update_and_broadcast` | jsonrpc | public +guest | `session_update_and_broadcast` | Update RTC session + broadcast |
| `/mail/rtc/channel/join_call` | jsonrpc | public +guest | `channel_call_join` | Join a channel's RTC call |
| `/mail/rtc/channel/leave_call` | jsonrpc | public +guest | `channel_call_leave` | Leave a call |
| `/mail/rtc/channel/upgrade_connection` | jsonrpc | user | `channel_upgrade` | Force SFU upgrade |
| `/mail/rtc/channel/cancel_call_invitation` | jsonrpc | public +guest | `channel_call_cancel_invitation` | Cancel ringing invitations |
| `/mail/rtc/audio_worklet_processor_v2` | http | public (readonly), GET | `audio_worklet_processor` | Serve the audio worklet JS |
| `/discuss/channel/ping` | jsonrpc | public +guest | `channel_ping` | RTC heartbeat + sync |

### controllers/discuss/gif.py — `DiscussGifController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/discuss/gif/search` | jsonrpc | user (readonly) | `search` | Proxy GIF search |
| `/discuss/gif/categories` | jsonrpc | user (readonly) | `categories` | Proxy GIF categories |
| `/discuss/gif/favorites` | jsonrpc | user (readonly) | `get_favorites` | List favorite GIFs |
| `/discuss/gif/add_favorite` | jsonrpc | user | `add_favorite` | Add a favorite GIF |
| `/discuss/gif/remove_favorite` | jsonrpc | user | `remove_favorite` | Remove a favorite GIF |

### controllers/discuss/search.py — `SearchController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/discuss/search` | jsonrpc | public +guest (readonly) | `search` | Search channels (+partners if logged in) |

### controllers/discuss/settings.py — `DiscussSettingsController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/discuss/settings/mute` | jsonrpc | user, POST | `discuss_mute` | Mute channel notifications for N minutes |
| `/discuss/settings/custom_notifications` | jsonrpc | user, POST | `discuss_custom_notifications` | Set custom notification level |

### controllers/discuss/voice.py — `VoiceController`
| Route | Type | Auth | Handler | Purpose |
|-------|------|------|---------|---------|
| `/discuss/voice/worklet_processor` | http | public (readonly), GET | `voice_worklet_processor` | Serve the voice-message worklet JS |

## Guest auth flow

The mail module registers **no custom Werkzeug auth method** (no `_auth_method_*`). Guest
access rides on ordinary `auth="public"` routes; a guest identity is layered in via the
`@add_guest_to_context` decorator, defined in **`tools/discuss.py`**:

1. Read the guest cookie `req.cookies.get(env["mail.guest"]._cookie_name, "")`.
2. Resolve it: `env["mail.guest"]._get_guest_from_token(token)`.
3. If valid, `req.update_context(guest=guest)` + `self.with_context(guest=guest)`; also set
   timezone from the `tz` cookie.

Cookie contract (`models/discuss/mail_guest.py`):
- `_cookie_name = "dgid"`, `_cookie_separator = "|"`.
- Value format: `"<guest_id>|<access_token>"` (`_format_auth_cookie`), set via
  `_set_auth_cookie` → `request.future_response.set_cookie(...)`.
- `_get_guest_from_token(token)` splits on `|`, rejects a non-digit id (returns an empty
  recordset — avoids a 500), `browse(int(id)).sudo().exists()`, validates the token with
  `consteq(...)` (constant-time), returns `guest.sudo(False)`.
- Handlers read the resolved guest via `_get_guest_from_context()` (asserts it is a
  `mail.guest` recordset of length ≤ 1).

Websocket auth uses the same cookie: `models/ir_websocket.py` +
`models/discuss/ir_websocket.py` call `_get_guest_from_token` for websocket / bus-channel
auth (guest bus channels are prefixed `mail.guest_`). `models/ir_http.py:session_info()`
injects guest data into `user_context` when there is no `request.session.uid` but a guest.

## Route count summary

| Group | Handlers | Files |
|-------|----------|-------|
| `controllers/` | 31 | thread (9), attachment (5), mail (4), mailbox (3), webclient (2), websocket (2), link_preview (2), message_reaction (1), google_translate (1), im_status (1), guest (1) — webmanifest = 0 |
| `controllers/discuss/` | 33 | channel (12), rtc (8), gif (5), public_page (4), settings (2), search (1), voice (1) |
| **Total** | **64** | **20** controller files (excluding the two `__init__.py`). One file contributes 0 routes — `webmanifest.py`; separately, the *class* `DiscussChannelWebclientController` in `channel.py` also declares none |

> **`thread.py` was 10 until `3d39ae624a0`**, which removed
> `/mail/thread/recipients/fields` (`mail_thread_recipients_fields`) — the route existed to
> hand the frontend the recipient field names, and the guard it needed on a caller-supplied
> model name was cheaper to delete than to keep. A search of history finds it; the routing map
> does not.
