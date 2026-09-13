from odoo import api, fields, models


class CalendarPopoverDeleteWizard(models.TransientModel):
    _name = "calendar.popover.delete.wizard"
    _inherit = ["mixin.mail.composer"]
    _description = "Calendar Popover Delete Wizard"

    calendar_event_id = fields.Many2one(comodel_name="calendar.event")
    delete = fields.Selection(
        selection=[
            ("one", "Delete this event"),
            ("next", "Delete this and following events"),
            ("all", "Delete all the events"),
        ],
        default="one",
    )
    recipient_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Recipients",
        compute="_compute_recipient_ids",
        readonly=False,
    )

    def close(self):
        """Apply the chosen policy, offering to notify the others first.

        Two outcomes, and the condition deciding between them used to be spelled
        `attendees_count != 1 or user_id.partner_id != partner_ids` -- a
        many2one compared against a many2many, which only reads as intended if
        you already know the count is 1. There is nobody to notify when the
        organizer is the only attendee, so that case deletes straight away;
        otherwise `action_unlink_event` opens the wizard's other view, which
        offers to mail the attendees before deleting.
        """
        self.check_singleton()
        event = self.calendar_event_id
        # Asked of `attendee_ids`, the authoritative invitation list, rather
        # than half of it of `partner_ids` -- which a many2many read strips of
        # archived contacts, so a meeting whose only other guest had been
        # deactivated counted as solo and was deleted with no offer to tell
        # them.
        organizer_is_sole_attendee = (
            event.attendee_ids.partner_id == event.user_id.partner_id
        )
        if organizer_is_sole_attendee:
            event._unlink_by_recurrence_policy(self.delete)
            return None
        return event.action_unlink_event(self.delete)

    @api.depends("calendar_event_id")
    def _compute_recipient_ids(self):
        """Compute the recipients by combining the record's partner and attendees partners."""
        for wizard in self:
            wizard.recipient_ids = (
                wizard.calendar_event_id.partner_id
                | wizard.calendar_event_id.attendee_ids.partner_id
            )

    @api.depends("calendar_event_id")
    def _compute_subject(self):
        """Compute the subject by rendering the template's subject field based on the event."""
        for wizard in self.filtered("template_id"):
            wizard.subject = wizard.template_id._render_field(
                "subject",
                [wizard.calendar_event_id.id],
                compute_lang=True,
                options={"post_process": True},
            )[wizard.calendar_event_id.id]

    @api.depends("calendar_event_id")
    def _compute_body(self):
        """Compute the body by rendering the template's body HTML field based on the event."""
        for wizard in self.filtered("template_id"):
            wizard.body = wizard.template_id._render_field(
                "body_html",
                [wizard.calendar_event_id.id],
                compute_lang=True,
                options={"post_process": True},
            )[wizard.calendar_event_id.id]

    def action_delete(self):
        """
        Delete the event based on the specified deletion type.

        :return: Action URL to redirect to the calendar view
        """
        self.check_singleton()
        # The policy reaches this wizard in either vocabulary -- its own
        # 'one'/'next'/'all' from the popover view, or `recurrence_update`'s
        # 'this'/'subsequent'/'all' from the calendar form
        # through action_unlink_event. `_unlink_by_recurrence_policy` accepts
        # both; before it existed, only 'next'/'all' triggered a mass deletion,
        # so "this and following" and "all events" from the form deleted nothing.
        self.calendar_event_id._unlink_by_recurrence_policy(
            self.env.context.get("default_recurrence")
        )

        return {"type": "ir.actions.act_url", "target": "self", "url": "/odoo/calendar"}

    def action_send_mail_and_delete(self):
        """Send email notification and delete the event based on the specified deletion type."""
        # `email_values` overrides the rendered `mail.mail` values, so this is
        # what actually sends the subject/body/recipients the user edited in
        # the popup -- re-rendering the bare template here (as this used to)
        # discarded every one of those edits.
        self.env.ref("calendar.calendar_template_delete_event").send_mail(
            self.calendar_event_id.id,
            email_layout_xmlid="mail.mail_notification_light",
            force_send=True,
            email_values={
                "subject": self.subject,
                "body_html": self.body,
                "partner_ids": [(6, 0, self.recipient_ids.ids)],
            },
        )
        return self.action_delete()
