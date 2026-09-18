import base64
import logging
from itertools import batched, zip_longest

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context

from odoo.addons.base.models.res_partner import _selection_timezones
from odoo.addons.calendar.models.utils import generate_calendar_token

_logger = logging.getLogger(__name__)


class CalendarAttendee(models.Model):
    """Calendar Attendee Information"""

    _name = "calendar.attendee"
    _inherit = ["mixin.calendar.privacy"]
    _rec_name = "common_name"
    _description = "Calendar Attendee Information"
    _order = "create_date ASC"
    _search_visibility_fields = ("event_id",)

    def _default_access_token(self):
        return generate_calendar_token()

    STATE_SELECTION = [
        ("accepted", "Yes"),
        ("declined", "No"),
        ("tentative", "Maybe"),
        ("needsAction", "Needs Action"),
    ]

    # event
    event_id = fields.Many2one(
        comodel_name="calendar.event",
        string="Meeting linked",
        index=True,
        required=True,
        ondelete="cascade",
    )
    recurrence_id = fields.Many2one(
        comodel_name="calendar.recurrence",
        related="event_id.recurrence_id",
    )
    # attendee
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Attendee",
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    email = fields.Char(
        related="partner_id.email",
        string="Email",
    )
    phone_ids = fields.Many2many(
        related="partner_id.phone_ids",
        string="Phone",
    )
    common_name = fields.Char(
        string="Common name",
        compute="_compute_common_name",
        store=True,
    )
    # `access_token` is the bearer credential of the `calendar` auth method:
    # holding one is enough to accept or decline an invitation from an
    # unauthenticated browser, and the controllers that do it sudo() without
    # checking who is calling. Any employee could read every attendee row, so
    # every token in the database was one search_read away from anyone.
    #
    # Restricted with `groups` rather than masked in `_fetch_query`, which is how
    # `calendar.event` hides its private fields: masking writes False into the
    # *shared* field cache, and a token is per-reader, so a masked read would be
    # served from cache to the very sudo() render that needs the real value --
    # emptying the accept/decline links of the invitation mail. `groups` is
    # checked at access time, keeps the cache honest, and sudo() bypasses it, so
    # the legitimate readers (mail templates, token controllers) still work.
    access_token = fields.Char(
        string="Invitation Token",
        default=_default_access_token,
        groups="base.group_system",
    )
    mail_tz = fields.Selection(
        selection=_selection_timezones,
        compute="_compute_mail_tz",
        help="Timezone used for displaying time in the mail template",
    )
    # state
    state = fields.Selection(
        selection=STATE_SELECTION,
        string="Status",
        default="needsAction",
    )

    _event_id_partner_id_unique = models.Constraint(
        "UNIQUE(event_id, partner_id)",
        "An attendee can only appear once per meeting.",
    )
    # `availability` (free/busy) used to be declared here: a stored column with
    # no reader, no writer and no view in any repo. The event's own `show_as`
    # carries that information.

    @api.depends("partner_id", "partner_id.name", "email")
    def _compute_common_name(self):
        for attendee in self:
            attendee.common_name = attendee.partner_id.name or attendee.email

    def _compute_mail_tz(self):
        for attendee in self:
            attendee.mail_tz = attendee.partner_id.tz

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            # by default, if no state is given for the attendee corresponding to the current user
            # that means he's the event organizer so we can set his state to "accepted"
            if (
                "state" not in values
                and values.get("partner_id") == self.env.user.partner_id.id
            ):
                values["state"] = "accepted"
            # A `common_name`-parsing block used to live here, trying to pull
            # an embedded `mailto:` address out of `values['common_name']`
            # into `values['email']`. Both fields are related/computed with
            # no inverse (`email` -> `partner_id.email`, `common_name` ->
            # `_compute_common_name`), so the ORM silently dropped whatever
            # was written into them -- dead code, confirmed by a live
            # `create()` call whose passed-in `common_name`/`email` never
            # landed on the record.
        attendees = super().create(vals_list)
        attendees.event_id.check_access("write")
        if not self.env.context.get(
            "is_calendar_event_new"
        ) and not self.env.context.get("skip_attendee_reservation_sync"):
            attendees.event_id._active_for_sync()._sync_reservations()
        return attendees

    def write(self, vals):
        # Check access on the event being left, not only the one landed on:
        # `event_id` is a plain writable field, so a write reassigning it only
        # checked the destination event, letting a user with no write access
        # to the origin event detach an attendee from it regardless.
        old_events = self.event_id
        res = super().write(vals)
        (old_events | self.event_id).check_access("write")
        if {
            "state",
            "event_id",
            "partner_id",
        } & vals.keys() and not self.env.context.get("skip_attendee_reservation_sync"):
            (old_events | self.event_id)._active_for_sync()._sync_reservations()
        return res

    def unlink(self):
        # `create()`/`write()` both route through `event_id.check_access('write')`;
        # `unlink()` had no equivalent, letting any internal user delete any
        # attendee off any event -- checked before deleting, since after
        # deletion the rows this check would query no longer exist.
        events = self.event_id
        events.check_access("write")
        self._unsubscribe_partner()
        result = super().unlink()
        if not self.env.context.get("skip_attendee_reservation_sync"):
            events.exists()._active_for_sync()._sync_reservations()
        return result

    def copy(self, default=None):
        raise UserError(_("You cannot duplicate a calendar attendee."))

    def _unsubscribe_partner(self):
        for event in self.event_id:
            partners = (
                event.attendee_ids & self
            ).partner_id & event.message_partner_ids
            event.message_unsubscribe(partner_ids=partners.ids)

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    @api.model
    def _mail_template_default_values(self):
        return {
            "email_from": "{{ (object.event_id.user_id.email_formatted or user.email_formatted or '') }}",
            "email_to": False,
            "partner_to": False,
            "lang": "{{ object.partner_id.lang }}",
            "use_default_to": True,
        }

    def _message_get_default_recipients_sources(self):
        # override: partner_id being the only stored field, we can currently
        # simplify computation, we have no other choice than relying on it
        return {
            attendee.id: {
                "partners": attendee.partner_id,
                "email_to_lst": [],
                "email_cc_lst": [],
            }
            for attendee in self
        }

    def _send_invitation_emails(self):
        """Hook to be able to override the invitation email sending process.
        Notably inside appointment to use a different mail template from the appointment type."""
        self._notify_attendees(
            self.env.ref(
                "calendar.calendar_template_meeting_invitation",
                raise_if_not_found=False,
            ),
            force_send=True,
        )

    def _notify_attendees(self, mail_template, notify_author=False, force_send=False):
        """Notify attendees about event main changes (invite, cancel, ...) based
        on template.

        :param mail_template: a mail.template record
        :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
        :return: None. Nothing reads the result; the early exits used to answer
            False and the ordinary one None, which said nothing either way.
        """
        # Cheapest and most certain first. The `force_send_limit` parameter and
        # the per-event `_skip_send_mail_status_update` sweep used to run above
        # these guards, so a database with `calendar.block_mail` set -- which
        # sends nothing at all -- still paid a config read and a pass over every
        # event on every notification.
        if isinstance(mail_template, str):
            raise ValueError(
                "Template should be a template record, not an XML ID anymore."
            )
        if not mail_template:
            _logger.warning(
                "No template passed to %s notification process. Skipped.", self
            )
            return
        if self.env.context.get("no_mail_to_attendees") or self.env[
            "ir.config_parameter"
        ].sudo().get_param("calendar.block_mail"):
            return

        recipients = self._notify_attendees_recipients(notify_author)
        if not recipients:
            return

        attachments_by_attendee = recipients._notify_attendees_attachments(
            mail_template
        )

        # Render the template once for all recipients instead of three times per
        # recipient inside the loop; _render_field already batches by id.
        #
        # sudo: the invitation body embeds each recipient's own `access_token` in
        # the accept/decline/view links, and `_fetch_query` masks that token for
        # every attendee but the reader -- so the organiser rendering invitations
        # for other people would otherwise produce links with an empty token.
        # Rendering is the one legitimate reader of somebody else's token; it
        # emits it only into the mail addressed to that person.
        rendering_template = mail_template.sudo()
        bodies = rendering_template._render_field(
            "body_html", recipients.ids, compute_lang=True
        )
        subjects = rendering_template._render_field(
            "subject", recipients.ids, compute_lang=True
        )
        emails_from = rendering_template._render_field("email_from", recipients.ids)

        mail_messages = self.env["mail.message"]
        for attendee in recipients:
            mail_messages += (
                attendee.event_id.with_context(no_document=True)
                .sudo()
                .message_notify(
                    email_from=emails_from[attendee.id]
                    or None,  # use None to trigger fallback sender
                    author_id=attendee.event_id.user_id.partner_id.id
                    or self.env.user.partner_id.id,
                    body=bodies[attendee.id],
                    subject=subjects[attendee.id],
                    notify_author=notify_author,
                    partner_ids=attendee.partner_id.ids,
                    email_layout_xmlid="mail.mail_notification_light",
                    attachment_ids=attachments_by_attendee.get(attendee.id, []),
                    force_send=False,
                )
            )
        # batch sending at the end
        if force_send:
            force_send_limit = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("mail.mail_force_send_limit", 100)
            )
            if len(recipients) < force_send_limit:
                mail_messages.sudo().mail_ids.send_after_commit()
        return

    def _notify_attendees_recipients(self, notify_author=False):
        """The attendees of `self` that a notification will actually reach.

        An e-mail address, not excluded by `_is_attendee_notification_required`, and on an
        event that does not opt out through `_skip_send_mail_status_update`.
        Everything the caller does afterwards is sized to this set and not to
        `self` -- copying an attachment or rendering a template for an attendee
        we never mail is pure waste, and since the copies carry
        `res_id=0`/`res_model='mail.compose.message'` the wasted ones are only
        reclaimed a day later by the mail autovacuum.

        :rtype: <calendar.attendee>
        """
        notified_ids = set(self.ids)
        for event, attendees in self.grouped("event_id").items():
            if event._skip_send_mail_status_update():
                notified_ids -= set(attendees.ids)
        return self.browse(notified_ids).filtered(
            lambda attendee: (
                attendee.email
                and attendee._is_attendee_notification_required(
                    notify_author=notify_author
                )
            )
        )

    def _notify_attendees_attachments(self, mail_template):
        """Attachment ids to put on each recipient's mail.

        Two sources, both one attachment record per recipient: the template's
        own attachments, and the .ics of the event that recipient is invited to.

        :rtype: dict[int, list[int]]
        """
        attachments_by_attendee = {attendee.id: [] for attendee in self}

        if mail_template.attachment_ids:
            # Setting res_model to ensure attachments are linked to the msg (otherwise only internal users are allowed link attachments)
            #
            # `copy()`, not `copy_data()` + `create()`: duplicating an
            # `ir.attachment` is split across the two. `copy_data` carries the
            # bytes only for database-stored content; filestore-backed content is
            # relinked to its existing file by `copy()` afterwards, deliberately
            # without reading it. Building the values and creating them here
            # skipped that relink, so every attendee received an attachment with
            # no content -- checksum unset, file_size 0 -- for any template
            # attachment held in the filestore, which is the normal case.
            #
            # One copy per recipient rather than one batched create: the relink
            # costs no bytes, and going through the API that actually duplicates
            # an attachment is what stops this regressing again.
            copied_ids = []
            for _recipient in self:
                copied_ids += mail_template.attachment_ids.copy(
                    {
                        "res_id": 0,
                        "res_model": "mail.compose.message",
                    }
                ).ids
            per_recipient = len(mail_template.attachment_ids)
            for attendee_id, ids in zip(
                self.ids,
                batched(copied_ids, per_recipient, strict=True),
                strict=True,
            ):
                attachments_by_attendee[attendee_id] += list(ids)

        # One create for every .ics rather than one per recipient inside the
        # posting loop: each recipient needs their own attachment record, but
        # they do not need their own round trip.
        ics_files = self.event_id._get_ics_file()
        with_ics = [
            attendee for attendee in self if ics_files.get(attendee.event_id.id)
        ]
        if with_ics:
            context = {
                **clean_context(self.env.context),
                "no_document": True,  # An ICS file must not create a document
            }
            ics_attachments = (
                self.env["ir.attachment"]
                .with_context(context)
                .create(
                    [
                        {
                            "datas": base64.b64encode(ics_files[attendee.event_id.id]),
                            "description": "invitation.ics",
                            "mimetype": "text/calendar",
                            "res_id": 0,
                            "res_model": "mail.compose.message",
                            "name": "invitation.ics",
                        }
                        for attendee in with_ics
                    ]
                )
            )
            for attendee, attachment in zip(with_ics, ics_attachments, strict=True):
                attachments_by_attendee[attendee.id].append(attachment.id)

        return attachments_by_attendee

    def _is_attendee_notification_required(self, notify_author=False):
        """Utility method that determines if the attendee should be notified.
        By default, we do not want to notify (aka no message and no mail) the current user
        if he is part of the attendees. But for reminders, mail_notify_author could be forced
        (Override in appointment to ignore that rule and notify all attendees if it's an appointment)
        """
        self.check_singleton()
        partner_not_sender = self.partner_id != self.env.user.partner_id
        return partner_not_sender or notify_author

    # ------------------------------------------------------------
    # STATE MANAGEMENT
    # ------------------------------------------------------------

    def do_tentative(self):
        """Makes event invitation as Tentative."""
        return self.write({"state": "tentative"})

    def do_accept(self):
        """Marks event invitation as Accepted."""
        self._log_answer(_("%s has accepted the invitation"))
        return self.write({"state": "accepted"})

    def do_decline(self):
        """Marks event invitation as Declined."""
        self._log_answer(_("%s has declined the invitation"))
        return self.write({"state": "declined"})

    def _log_answer(self, body_format):
        """Log each attendee's answer on its own event, in as few rounds as possible.

        `message_post` is `check_singleton`, so a loop over `self` paid a full post
        per attendee: answering a twenty-occurrence series posted twenty
        messages one at a time. Measured at **5.39 queries per attendee**,
        attributed by control -- `do_tentative` performs the same `write` with
        no message and is flat (one query for twenty attendees).

        The thread is the *event*, so a batch may carry at most one attendee per
        event; attendees are dealt into rounds on that basis. The case that
        motivates this -- one person answering a whole series -- is a single
        round, because each occurrence is its own event.

        :param body_format: a translated format string taking the common name.
        """
        if not self:
            return
        subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "calendar.subtype_invitation", raise_if_not_found=False
        )
        by_event = [list(attendees) for attendees in self.grouped("event_id").values()]
        for round_attendees in zip_longest(*by_event):
            answering = [
                attendee
                for attendee in round_attendees
                if attendee is not None and attendee.event_id
            ]
            if not answering:
                continue
            events = self.env["calendar.event"].browse(
                attendee.event_id.id for attendee in answering
            )
            events._message_post_batch(
                bodies={
                    attendee.event_id.id: body_format % attendee.common_name
                    for attendee in answering
                },
                authors={
                    attendee.event_id.id: attendee.partner_id.id
                    for attendee in answering
                },
                subtype_id=subtype_id,
            )
