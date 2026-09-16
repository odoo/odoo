# Mail Module Model Map

Every Python model defined or extended by the `mail` module (`addons/mail`),
grouped by concern, with `_name`/`_inherit`, model kind, key fields and methods.

> **Every mixin lives in `models/mixin_<what it adds>.py`.** `coding_guidelines.rst` §2.2.1
> made the marker a prefix, not a suffix, workspace-wide: `mail.thread` is
> `mixin.mail.thread` in `mixin_mail_thread.py`, class `MixinMailThread`, xmlid
> `model_mixin_mail_thread`. A vanilla name from training data — `mail.thread`,
> `mail.activity.mixin` — does not exist and raises. Workspace CLAUDE.md §11b has the
> transform.

> **See also**: `ARCHITECTURE.md` (module identity, request flow), `CONVENTIONS.md`
> (the `mixin.mail.thread` mixin contract, `message_post`, tracking, gateway), `ROUTE_MAP.md`
> (HTTP/RPC endpoints), `STATE_MANAGEMENT.md` (the JS-side `Store`/`Record` mirror of
> these models).

Kind legend: **[M]** `models.Model` · **[A]** `models.AbstractModel` (mixin/framework) ·
**[T]** `models.TransientModel` (wizard). Paths are relative to `models/` unless noted.

## The mixin architecture (why this module is different)

`mail` is mostly **abstract mixins injected into other models**. A business model becomes
"mail-enabled" by adding `mixin.mail.thread` (+ optionally `mixin.mail.activity`) to its
`_inherit` list — it then gets the chatter, followers, tracking, and email gateway for
free. The heavy public API therefore lives on **abstract** models. The `base` model
(`base.py`, `_inherit = "base"`) also carries mail helpers so that **every** Odoo model
has them (suggested-recipients, partner resolution, low-level tracking).

## 1. Thread / messaging core

### Mixins (injected into business models)

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `base.py` | inh `base` | A | Injects mail helpers into **every** model (suggested recipients, partner resolution, `_mail_track`) |
| `mixin_mail_thread.py` | `mixin.mail.thread` | A | Master messaging / gateway / notification / tracking mixin |
| `mixin_mail_thread_blacklist.py` | `mixin.mail.thread.blacklist` (inh `mixin.mail.thread`) | A | Email blacklist + bounce management |
| `mixin_mail_thread_cc.py` | `mixin.mail.thread.cc` (inh `mixin.mail.thread`) | A | Email CC (`email_cc`) tracking |
| `mixin_mail_thread_main_attachment.py` | `mixin.mail.thread.main.attachment` (inh `mixin.mail.thread`) | A | "Main attachment" management |
| `mixin_mail_gateway.py` | `mixin.mail.gateway` | A | Inbound-email routing: parse, match a thread, decide the route (`mixin.mail.thread` inherits it) |
| `mixin_mail_attachment_owner.py` | `mixin.mail.attachment.owner` | A | Re-owns the attachments a create/write links, for `mail.template` and `mailing.mailing` |
| `mixin_store_sync.py` | `mixin.store.sync` (inh `mixin.bus.listener`) | A | Broadcasts the store fields a write changed (`discuss.channel`, `discuss.channel.member`) |
| `mixin_mail_presence.py` | `mixin.mail.presence` | A | `im_status` / `offline_since` with their access tokens and the `avatar_128` / `im_status` store shapes, shared by `res.partner` and `mail.guest` (both also `mixin.avatar`); each keeps its own `_compute_presence` |

### Data models

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `mail_message.py` | `mail.message` (inh `mixin.bus.listener`) | M | Core message record |
| `mail_message_access.py` | inh `mail.message` | M | The access rule and nothing else — `_check_access`, `_search`, `_get_forbidden_access` and its `_discard_*` rounds. Split out of `mail_message.py` so the rule has one home |
| `mail_message_store.py` | inh `mail.message` | M | The client payload — `_to_store` and its defaults |
| `mail_mail.py` | `mail.mail` (**`_inherits`** `mail.message` via `mail_message_id`) | M | Outgoing email record + send queue |
| `mail_followers.py` | `mail.followers` | M | Document followers (per res_model/res_id) |
| `mail_notification.py` | `mail.notification` | M | Per-recipient delivery status |
| `mail_message_subtype.py` | `mail.message.subtype` | M | Subtypes (subscription granularity) |
| `mail_message_reaction.py` | `mail.message.reaction` | M | Emoji reactions |
| `mail_message_translation.py` | `mail.message.translation` | M | On-demand message translations |
| `mail_message_schedule.py` | `mail.message.schedule` | M | Deferred posting of a pending message |
| `mail_scheduled_message.py` | `mail.scheduled.message` | M | User-scheduled (future) messages |
| `mail_link_preview.py` | `mail.link.preview` (inh `mixin.bus.listener`) | M | URL preview data store |
| `mail_message_link_preview.py` | `mail.message.link.preview` (inh `mixin.bus.listener`) | M | M2M join: message ↔ link preview |
| `mail_canned_response.py` | `mail.canned.response` | M | `::shortcut` canned responses |

## 2. Render / template / composer / tracking

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `mixin_mail_render.py` | `mixin.mail.render` | A | QWeb + inline-template rendering engine |
| `mixin_mail_composer.py` | `mixin.mail.composer` (inh `mixin.mail.render`) | A | Subject/body dynamic-template compute |
| `mail_template.py` | `mail.template` (inh `mixin.mail.render`, `mixin.template.reset`) | M | Email templates |
| `mixin_template_reset.py` | `mixin.template.reset` | A | Reset a template to its module source |
| `mail_tracking_value.py` | `mail.tracking.value` | M | Old/new value rows for field tracking |
| `mixin_mail_tracking_duration.py` | `mixin.mail.tracking.duration` (inh `mixin.mail.thread`) | A | Time-in-stage + "rotting" computation |

## 3. Activity

| File | `_name` | Kind | Role |
|------|---------|------|------|
| `mail_activity.py` | `mail.activity` | M | Activity / to-do record |
| `mixin_mail_activity.py` | `mixin.mail.activity` | A | Adds activities to a model |
| `mail_activity_type.py` | `mail.activity.type` | M | Activity type configuration |
| `mail_activity_plan.py` | `mail.activity.plan` | M | Activity plan (bundle of activities) |
| `mail_activity_plan_template.py` | `mail.activity.plan.template` | M | Plan line template |
| `mixin_delay.py` | `mixin.delay` | A | The "N time units" half of a scheduled offset, shared by `mail.activity.type` and `mail.activity.plan.template`; `delay_from` stays with the consumer |

## 4. Alias / mail gateway

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `mail_alias.py` | `mail.alias` | M | Incoming-email alias (routing target) |
| `mail_alias_domain.py` | `mail.alias.domain` | M | Catchall / bounce / default-from domain |
| `mixin_mail_alias.py` | `mixin.mail.alias` (inh `mixin.mail.alias.optional`; `_inherits` `mail.alias` via `alias_id`) | A | Required-alias mixin |
| `mixin_mail_alias_optional.py` | `mixin.mail.alias.optional` | A | Optional-alias mixin |
| `mail_gateway_allowed.py` | `mail.gateway.allowed` | M | Allowlist bypassing loop detection |
| `fetchmail.py` | `fetchmail.server` | M | Incoming POP/IMAP server config |

## 5. Blacklist / presence / push / misc

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `mail_blacklist.py` | `mail.blacklist` (inh `mixin.mail.thread`) | M | Blacklisted email addresses |
| `mail_presence.py` | `mail.presence` (inh `mixin.bus.listener`) | M | User/guest online presence |
| `mail_push.py` | `mail.push` | M | Queued web-push notification |
| `mail_push_device.py` | `mail.push.device` | M | Registered push device / endpoint |
| `mail_ice_server.py` | `mail.ice.server` | M | WebRTC ICE / STUN / TURN config |
| `update.py` | `publisher_warranty.contract` | A | Publisher-warranty / update ping |

## 6. Discuss (`models/discuss/`)

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `discuss_channel.py` | `discuss.channel` (inh `mixin.mail.thread`, `mixin.bus.listener`) | M | Chat / discussion channel |
| `discuss_channel_member.py` | `discuss.channel.member` (inh `mixin.bus.listener`) | M | Membership + read/seen state |
| `discuss_channel_rtc_session.py` | `discuss.channel.rtc.session` (inh `mixin.bus.listener`) | M | Active RTC (call) session |
| `discuss_call_history.py` | `discuss.call.history` | M | Call history log |
| `discuss_gif_favorite.py` | `discuss.gif.favorite` | M | Favorite Tenor GIFs |
| `discuss_voice_metadata.py` | `discuss.voice.metadata` | M | Voice-message attachment metadata |
| `mail_guest.py` | `mail.guest` (inh `mixin.avatar`, `mixin.mail.presence`, `mixin.bus.listener`) | M | Portal / anonymous guest identity |
| `mixin_bus_listener.py` | inh `mixin.bus.listener` | A | Bus-notify helper (mail extensions) |
| `mail_message.py` | inh `mail.message` | M | Discuss extensions to messages |
| `ir_attachment.py`, `ir_websocket.py`, `res_groups.py`, `res_partner.py`, `res_users.py` | inh respective | M/A | Discuss extensions of framework/user models |

## 7. Framework `ir.*` extensions (`_inherit`)

All extend an existing framework model; most add mail behavior.

- `ir_actions_server.py` → `ir.actions.server` (**+`mixin.mail.thread`, `mixin.mail.activity`**) [M]
- `ir_cron.py` → `ir.cron` (**+`mixin.mail.thread`, `mixin.mail.activity`**) [A]
- `ir_attachment.py` [M] · `ir_http.py` [A] · `ir_qweb.py` [A]
- `ir_websocket.py` [A] · `ir_ui_view.py` · `ir_ui_menu.py` · `ir_model.py`
- `ir_model_fields.py` · `ir_config_parameter.py` · `ir_mail_server.py`

> **There is no `ir.binary` extension in `mail`.** Two 0-byte `ir_binary.py` placeholders used
> to sit in `models/` and `models/discuss/`, imported by neither `__init__.py`; both are now
> deleted. A search that turns one up is reading history.

## 8. `res.*` user / partner / company

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `res_partner.py` | `res.partner` (**+`mixin.mail.activity`, `mixin.mail.presence`, `mixin.mail.thread.blacklist`**) | M | Partner mail behavior |
| `res_users.py` | `res.users` | M | User notification prefs, presence |
| `res_company.py` | `res.company` | M | Company alias/catchall config |
| `res_config_settings.py` | `res.config.settings` | T | Discuss/mail settings |
| `res_role.py` | `res.role` (new `_name`) | M | Roles (@-mention groups) |
| `res_users_settings.py` | `res.users.settings` | M | Per-user discuss settings |
| `res_users_settings_volumes.py` | `res.users.settings.volumes` (new `_name`) | M | Per-partner RTC volume prefs |

## 9. Wizards (`wizards/`)

| File | `_name` / `_inherit` | Kind | Role |
|------|----------------------|------|------|
| `mail_compose_message.py` | `mail.compose.message` (inh `mixin.mail.composer`) | T | Email composition wizard |
| `mail_activity_schedule.py` | `mail.activity.schedule` | T | Schedule activities / run a plan |
| `mail_activity_schedule_summary.py` | `mail.activity.schedule.line` | T | Plan schedule summary line |
| `mail_blacklist_remove.py` | `mail.blacklist.remove` | T | Remove-from-blacklist wizard |
| `mail_followers_edit.py` | `mail.followers.edit` | T | Add / edit followers |
| `mail_template_preview.py` | `mail.template.preview` | T | Template preview |
| `mail_template_reset.py` | `mail.template.reset` | T | Reset template to source |
| `base_module_uninstall.py` | inh `base.module.uninstall` | T | Uninstall hook |
| `base_partner_merge_automatic_wizard.py` | inh `base.partner.merge.automatic.wizard` | T | Partner-merge hook |

---

## Core mixin API — `mixin.mail.thread` (`mixin_mail_thread.py`)

The canonical messaging surface. Grouped by concern.

**Posting / logging** (the primary public entry points):
- `message_post(**kwargs)` — post a message on the record (central entry point)
- `message_post_with_source(source_ref, ...)` — post rendering a view/template source
- `message_mail_with_source(source_ref, ...)` — send email (no persisted thread message)
- `message_notify(...)` — send a notification not stored as a thread message
- `_message_log(...)` / `_message_log_batch(...)` / `_message_log_with_view(...)` — internal-note logging
- `_message_create(values_list)` — low-level create bypassing the post pipeline

**Subscription (followers)**:
- `message_subscribe(partner_ids=None, subtype_ids=None)` / `_message_subscribe(...)`
- `message_unsubscribe(partner_ids=None)`
- `_message_auto_subscribe(updated_values, ...)`, `_message_auto_subscribe_followers(...)`, `_message_auto_subscribe_notify(...)`
- `message_get_followers(...)`, `_message_followers_to_store(...)`

**Notification dispatch**:
- `_notify_thread(message, msg_vals=False, **kwargs)` — dispatch entry
- `_notify_thread_by_inbox(...)`, `_notify_thread_by_email(...)`, `_notify_thread_by_web_push(...)`
- `_notify_get_recipients(...)`, `_notify_get_recipients_groups(...)`, `_notify_get_recipients_classify(...)`
- `_notify_by_email_prepare_rendering_context(...)`, `_notify_by_email_get_base_mail_values(...)`, `_notify_by_email_get_final_mail_values(...)`

**Incoming gateway (email → record)**:
- `message_process(...)`, `message_route(...)`, `_message_route_process(...)`, `_routing_check_route(...)`
- `message_new(msg_dict, custom_values=None)` / `message_update(msg_dict, update_vals=None)` — create/update hooks
- `message_parse(message, ...)`, `_message_parse_extract_payload(...)`, `_message_parse_extract_bounce(...)`
- `_routing_handle_bounce(...)`, `_routing_create_bounce_email(...)`, `_is_bounce(...)`, `_is_loop_sender(...)`, `_has_loop_headers(...)`

**Field tracking** (see CONVENTIONS.md gotcha on tracking):
- `_track_prepare(fields_iter)`, `_track_finalize()`, `_track_discard()`, `_track_filtered_for_display(...)`
- `_track_subtype(initial_values)`, `_track_template(changes)`, `_track_get_fields()`, `_track_set_author(...)`, `_track_set_log_message(...)`
- `_message_track(fields_iter, initial_values_dict)`, `_message_track_post_template(changes)`

**Compute helpers**: `_message_compute_author(...)`, `_message_compute_real_author(...)`, `_message_compute_parent_id(...)`, `_message_compute_subject()`.
**After-hooks**: `_message_post_after_hook(message, msg_values)`, `_message_mail_after_hook(mails)`.

> **On `base.py`, not `mixin_mail_thread.py`** — suggested and default recipients
> (`_message_get_suggested_recipients_sources`, `_message_get_suggested_recipients_batch`,
> `_message_get_suggested_recipients`, `_message_get_default_recipients_sources`,
> `_message_get_default_recipients`, `_message_add_suggested_recipients_from_replies`),
> partner resolution (`_mail_get_partners`, `_mail_get_partner_fields`, `_mail_get_customer`,
> `_mail_get_companies`, `_partner_get_or_create_from_emails`, `_partner_get_or_create_from_emails_single`),
> reply-to (`_notify_get_reply_to`), and low-level tracking (`_mail_track`) live on the `base`
> inherit so **every** model has them. `mixin.mail.thread.cc` overrides
> `_message_get_suggested_recipients_sources`.
>
> **The `_get_*_sources` names are load-bearing.** `_message_add_suggested_recipients` and
> `_message_add_default_recipients` added nothing — each built a mapping and returned it — so
> each is now `_message_get_*_sources`, one named step in a pipeline. The one that kept `_add_`
> is `_message_add_suggested_recipients_from_replies`, and the contrast is the point: it
> mutates in place and returns None. **An override written against an old name is silently
> inert**, which is the failure mode a rename has and no gate catches.
>
> **Note:** the gateway *user* resolvers `_mail_get_or_create_partner_from_emails` and
> `_mail_get_user_for_gateway` are on **`mixin_mail_thread.py`**, not `base.py` — they are
> gateway-specific, not needed on every model. `_partner_get_or_create_from_emails` is **not** one of
> them: it is on `base.py`, and `mixin_mail_thread.py` reaches it through the MRO.

**`mixin.mail.thread` fields injected into the document**: `message_is_follower`,
`message_follower_ids` (O2m→`mail.followers`), `message_partner_ids` (M2m→`res.partner`),
`message_ids` (O2m→`mail.message`), `has_message`, `message_needaction`,
`message_needaction_counter`, `message_has_error`, `message_has_error_counter`,
`message_attachment_count`.

## Other mixin APIs (condensed)

**`mixin.mail.thread.blacklist`** — `_compute_is_blacklisted`/`_search_is_blacklisted`,
`_message_receive_bounce`, `_message_reset_bounce`, `mail_action_blacklist_remove`,
`_get_domain_loop_sender`. Fields: `email_normalized`, `is_blacklisted`, `message_bounce`.

**`mixin.mail.thread.cc`** — `_mail_cc_sanitized_raw_dict(cc_string)`, `message_new`,
`message_update`, `_message_get_suggested_recipients_sources`. Field: `email_cc`.

**`mixin.mail.thread.main.attachment`** — `_message_post_after_hook`,
`_message_set_main_attachment_id(...)`, `_thread_to_store(...)`. Field: `message_main_attachment_id`.

**`mixin.mail.activity`** — `activity_schedule(...)`, `_activity_schedule_with_view(...)`,
`activity_reschedule(...)`, `activity_feedback(...)`, `activity_unlink(...)`,
`activity_search(...)`, `activity_send_mail(template_id)`,
`action_reschedule_my_next_today/tomorrow/nextweek`. Fields: `activity_ids`,
`activity_state`, `activity_user_id`, `activity_type_id`, `activity_date_deadline`,
`my_activity_date_deadline`, `activity_summary`, `activity_exception_decoration`.

**`mixin.mail.render`** — `_render_template(...)`, `_render_template_qweb(...)`,
`_render_template_qweb_view(...)`, `_render_template_inline_template(...)`,
`_render_field(...)`, `_render_lang(...)`, `_render_eval_context()`,
`_replace_local_links(...)`, `_process_scheduled_date(...)`, `_has_unsafe_expression(...)`,
`_check_access_right_dynamic_template()`. (See CONVENTIONS.md on QWeb-vs-inline templating.)

**`mixin.mail.composer`** — `_compute_subject`, `_compute_body`,
`_compute_body_has_template_value`, `_compute_lang`, `_compute_can_edit_body`, `_render_field`.

**`mixin.mail.tracking.duration`** — `_compute_duration_tracking`,
`_compute_rotting`/`_search_is_rotting`, `_get_duration_from_tracking(trackings)`,
`_get_rotting_depends_fields()`, `_get_domain_rotting_records()`, `_is_rotting_feature_enabled()`.

**`mixin.template.reset`** — `reset_template()`, `_override_translation_term(...)`, `_load_records_write`.

## Central data models — key fields + methods

### `mail.message` (`mail_message.py`)
Fields: `subject`, `date`, `body`, `preview`, `message_type`, `subtype_id`, `model`+`res_id`
(document ref), `record_name`, `record_alias_domain_id`, `mail_activity_type_id`,
`parent_id`/`child_ids`, `author_id`, `author_guest_id`, `email_from`, `partner_ids`
(recipients), `notified_partner_ids`, `notification_ids` (O2m→`mail.notification`),
`attachment_ids`, `tracking_value_ids`, `starred_partner_ids`, `reaction_ids`,
`message_link_preview_ids`, `needaction`, `has_error`, `is_internal`, `pinned_at`,
`message_id`, `reply_to`, `email_layout_xmlid`, `mail_ids` (O2m→`mail.mail`).
Methods: `create`, `write`, `unlink`, `_get_with_access`, `mark_all_as_read`,
`set_message_done`, `toggle_message_starred`, `_message_fetch(...)`, `_message_reaction(...)`,
`_filtered_empty()`, `_get_message_id(values)`.

> **`mail.message` is spread over three files** — `mail_message.py` (the model),
> `mail_message_access.py` (`_check_access`, `_search`, `_get_forbidden_access` + its
> `_discard_*` rounds) and `mail_message_store.py` (`_to_store`), plus
> `discuss/mail_message.py` for the Discuss extensions. The access rule is written twice by
> design — forward in `_search.allowed()` and backward in `_get_forbidden_access` — and
> `test_mail_message_access_parity` pins the two spellings against each other. Change one side
> and that test is the one that tells you about the other.

### `mail.mail` (`mail_mail.py`, `_inherits = {"mail.message": "mail_message_id"}`)

> Delegation inheritance, **not** `_inherit`: `mail.mail` is a separate table with a
> required FK `mail_message_id` to `mail.message`, transparently delegating message-field
> reads/writes. Deleting a `mail.mail` does not delete its `mail.message` unless configured.
Fields: `mail_message_id`, `body_html`, `body_content`, `references`, `headers`, `state`
(outgoing/sent/exception/cancel), `failure_type`, `failure_reason`, `email_to`, `email_cc`,
`recipient_ids`, `is_notification`, `auto_delete`, `scheduled_date`, `fetchmail_server_id`,
`unrestricted_attachment_ids`.
Methods: `create`, `process_email_queue(...)`, `send(auto_commit, raise_exception, ...)`,
`_send(...)`, `send_after_commit()`, `mark_outgoing()`, `cancel()`, `action_retry()`,
`_prepare_outgoing_list(...)`, `_split_by_mail_configuration()`.

### `mail.followers` (`mail_followers.py`, `_log_access = False`)
Fields: `res_model`, `res_id`, `partner_id`, `subtype_ids`, `is_active` (related to
`partner_id.active`). Constraint `unique(res_model, res_id, partner_id)`.
Methods: `_add_followers(...)` (subscribe partners with the model's default subtypes),
`_add_followers_multi(...)` (subscribe a sparse `{res_id: {partner_id: subtype_ids}}` map —
the way in when the caller already knows the subtypes), `_prepare_followers_vals(...)`
(decides, writes nothing), `_create_followers(...)` (one `INSERT ... ON CONFLICT DO NOTHING`;
the rows it does not get back *are* the raced pairs), `_get_recipient_data(...)`,
`_get_subscription_data(...)`, `_invalidate_documents(...)`.

> **Three policies, not four.** `existing_policy` is `skip` / `replace` / `update`. `force`
> existed to unlink and re-create, and read the dense `res_ids x partner_ids` product back out
> of a request that is sparse per record — so it unsubscribed pairs no caller had named. It is
> gone; `replace` reaches the same end state and keeps the row id.
>
> **The recipient payload is built in one place**, `mail/tools/recipients.py`'s
> `prepare_recipient_data()`, by `mail.followers` and by all four other producers. `type` is
> derived there from `(partner_share, user_share)` rather than re-decided per producer, which is
> how a share partner used to be a `portal` recipient in one place and a `customer` in another.
> `test_lint`'s `TestRecipientData` gates the *keys*; the constructor is what agrees the values.

> **Two renames here, and both are traps.** `_insert_followers` is now `_add_followers` —
> `_insert_` is reserved for SQL DML and this method creates ORM records; and the *old*
> `_add_followers`, which returned payloads rather than creating anything, is now
> `_prepare_followers_vals`. So `_add_followers` exists both before and after and **means
> something different**: a call site carried over unchanged compiles and does the wrong thing.
>
> **`name` and `email` are gone, deliberately.** `mail.followers` is readable by every internal
> user and carries no record rule, and `related` fields default to `related_sudo=True`, so both
> answered for partners the ACL denies — and rode the chatter Store payload, a hundred rows per
> open. Nothing read either one in Python or JS. `is_active` and `display_name` stay because the
> client uses them. Do not re-add a `related` field here without checking the ACL it crosses.

### `mail.notification` (`mail_notification.py`, `_rec_name="res_partner_id"`)
Fields: `author_id`, `mail_message_id` (req), `mail_mail_id`, `res_partner_id`,
`mail_email_address`, `notification_type` (inbox/email/sms/…), `notification_status`
(ready/sent/bounce/exception/canceled), `is_read`, `read_date`, `failure_type`, `failure_reason`.
Methods: `_gc_notifications(max_age_days=180)`, `format_failure_reason()`,
`_filtered_for_web_client()`, `_to_store_defaults(...)`.

### `mail.activity` (`mail_activity.py`, `_rec_name="summary"`)
Fields: `res_model_id`/`res_model`/`res_id`/`res_name`, `activity_type_id`, `activity_category`,
`summary`, `note`, `date_deadline`, `date_done`, `state` (overdue/today/planned/done),
`user_id`, `automated`, `attachment_ids`, `mail_template_ids`, `chaining_type`,
`recommended_activity_type_id`, `active`.
Methods: `action_feedback(...)`, `action_done(...)`, `_action_done(...)`,
`action_feedback_schedule_next(...)`, `action_cancel()`, `action_notify()`,
`get_activity_data(...)`, `activity_format()`, `_gc_remove_old_overdue_activities()`.

### `mail.template` (`mail_template.py`)
Fields: `name`, `model_id`/`model`, `subject`, `email_from`, `use_default_to`, `email_to`,
`partner_to`, `email_cc`, `reply_to`, `body_html`, `attachment_ids`, `report_template_ids`,
`email_layout_xmlid`, `mail_server_id`, `scheduled_date`, `auto_delete`, `ref_ir_act_window`.
Methods: `send_mail(res_id, ...)`, `send_mail_batch(...)`, `create_action()`,
`unlink_action()`, `_parse_partner_to(partner_to)`, and the payload pipeline —
`_prepare_static_vals(...)`, `_prepare_recipient_vals(...)`, `_prepare_attachment_vals(...)`,
`_prepare_scheduled_date_vals(...)`, `_prepare_mail_vals(...)`.

> **The `_generate_template*` names are gone.** The four payload builders are `_prepare_*`
> under §2.4's discriminator — the caller answers it, since `send_mail_batch` passes the result
> straight into `mail.mail.create`. Once renamed, the stages are visibly one pipeline; that is
> what the rename was for.

### `mail.alias` (`mail_alias.py`, `_rec_name="alias_name"`)
Fields: `alias_name`, `alias_full_name`, `alias_domain_id`/`alias_domain`, `alias_model_id`,
`alias_defaults`, `alias_force_thread_id`, `alias_parent_model_id`, `alias_parent_thread_id`,
`alias_contact` (everyone/partners/followers), `alias_incoming_local`, `alias_bounced_content`,
`alias_status`.
Methods: `_check_unique(...)`, `_normalize_alias_name(name, ...)`, `open_document()`,
`_alias_bounce_incoming_email(...)`, `_get_alias_bounced_body(...)`, `_get_alias_contact_description()`.

### `mail.tracking.value` (`mail_tracking_value.py`, `_rec_name="field_id"`)
Fields: `field_id` (→`ir.model.fields`), `field_info` (Json),
`old_value_integer/float/char/text/datetime`, `new_value_*`, `currency_id`, `mail_message_id`.
Methods: `_prepare_tracking_values(...)`, `_prepare_tracking_values_property(...)`,
`_tracking_value_format()`, `_format_display_value(...)`, `_filtered_has_field_access(env)`.

### `mail.message.subtype` (`mail_message_subtype.py`)
Fields: `name`, `description`, `internal`, `parent_id`, `relation_field`, `res_model`,
`default`, `sequence`, `hidden`, `track_recipients`.
Methods: `_get_auto_subscription_subtypes(model_name)`, `default_subtypes(model_name)`,
`_get_subtypes(model_name)`.

## Model Index (file → model → role)

| File | Model | Role |
|------|-------|------|
| `base.py` | base | Mail helpers on every model |
| `mixin_mail_thread.py` | mixin.mail.thread | Master messaging mixin |
| `mail_message.py` | mail.message | Message record |
| `mail_message_access.py` | mail.message (inh) | The access rule, both spellings |
| `mail_message_store.py` | mail.message (inh) | `_to_store` client payload |
| `mail_mail.py` | mail.mail | Outgoing email + queue |
| `mail_followers.py` | mail.followers | Followers |
| `mail_notification.py` | mail.notification | Per-recipient status |
| `mail_activity.py` | mail.activity | Activities |
| `mixin_mail_activity.py` | mixin.mail.activity | Activity mixin |
| `mail_template.py` | mail.template | Email templates |
| `mixin_mail_render.py` | mixin.mail.render | Template rendering |
| `mail_alias.py` | mail.alias | Incoming alias |
| `mail_tracking_value.py` | mail.tracking.value | Field tracking rows |
| `discuss/discuss_channel.py` | discuss.channel | Chat channel |
| `discuss/discuss_channel_member.py` | discuss.channel.member | Membership + read state |
| `discuss/discuss_channel_rtc_session.py` | discuss.channel.rtc.session | Call session |
| `discuss/mail_guest.py` | mail.guest | Anonymous guest identity |
| `mail_push.py` / `mail_push_device.py` | mail.push / mail.push.device | Web-push queue + devices |
| `wizards/mail_compose_message.py` | mail.compose.message | Composer wizard |
