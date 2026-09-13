from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class CalendarAlarm(models.Model):
    _name = "calendar.alarm"
    _description = "Event Alarm"

    _interval_selection = {"minutes": "Minutes", "hours": "Hours", "days": "Days"}

    name = fields.Char(
        translate=True,
        required=True,
    )
    alarm_type = fields.Selection(
        selection=[("notification", "Notification"), ("email", "Email")],
        string="Type",
        default="email",
        required=True,
    )
    duration = fields.Integer(
        string="Remind Before",
        default=1,
        required=True,
    )
    interval = fields.Selection(
        selection=list(_interval_selection.items()),
        string="Unit",
        default="hours",
        required=True,
    )
    duration_minutes = fields.Integer(
        string="Duration in minutes",
        compute="_compute_duration_minutes",
        search="_search_duration_minutes",
        store=True,
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        compute="_compute_mail_template_id",
        store=True,
        readonly=False,
        domain=[("model", "in", ["calendar.attendee"])],
        help="Template used to render mail reminder content.",
    )
    body = fields.Text(
        string="Additional Message",
        help="Additional message that would be sent with the notification for the reminder",
    )
    notify_responsible = fields.Boolean(default=False)
    notify_responsible_available = fields.Boolean(
        compute="_compute_notify_responsible_available",
        help="Technical: whether this alarm's channel can single out the organizer.",
    )

    @api.constrains("duration")
    def _check_duration(self):
        for alarm in self:
            if alarm.duration < 0:
                raise ValidationError(_("The reminder delay cannot be negative."))

    @api.depends("alarm_type")
    def _compute_notify_responsible_available(self):
        responsible_aware = self._get_responsible_aware_alarm_types()
        for alarm in self:
            alarm.notify_responsible_available = alarm.alarm_type in responsible_aware

    @api.depends("interval", "duration")
    def _compute_duration_minutes(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_minutes = alarm.duration
            elif alarm.interval == "hours":
                alarm.duration_minutes = alarm.duration * 60
            elif alarm.interval == "days":
                alarm.duration_minutes = alarm.duration * 60 * 24
            else:
                alarm.duration_minutes = 0

    @api.depends("alarm_type", "mail_template_id")
    def _compute_mail_template_id(self):
        for alarm in self:
            if alarm.alarm_type == "email" and not alarm.mail_template_id:
                alarm.mail_template_id = self.env["ir.model.data"]._xmlid_to_res_id(
                    "calendar.calendar_template_meeting_reminder"
                )
            elif alarm.alarm_type != "email" or not alarm.mail_template_id:
                alarm.mail_template_id = False

    def _search_duration_minutes(self, operator, value):
        if operator == "in":
            # recursive call with operator '='
            return Domain.OR(self._search_duration_minutes("=", v) for v in value)
        elif operator == "=":
            if not value:
                return Domain("duration", "=", False)
        elif operator not in (">=", "<=", "<", ">"):
            return NotImplemented
        return [
            "|",
            "|",
            "&",
            ("interval", "=", "minutes"),
            ("duration", operator, value),
            "&",
            ("interval", "=", "hours"),
            ("duration", operator, value / 60),
            "&",
            ("interval", "=", "days"),
            ("duration", operator, value / 60 / 24),
        ]

    @api.model
    def _get_responsible_aware_alarm_types(self):
        """Alarm types for which "Notify Responsible" is meaningful.

        Empty in the base module: an email or an in-app notification reaches the
        organizer through their attendee record like everybody else. The channels
        that added the flag own the answer -- `calendar_sms` and
        `whatsapp_calendar` extend `alarm_type` and read `notify_responsible` in
        their own senders -- so they extend this instead of the base module
        hardcoding a list of its own two types and negating it, which silently
        stopped meaning what it says the moment a third type was added.
        """
        return set()

    @api.onchange("duration", "interval", "alarm_type", "notify_responsible")
    def _onchange_duration_interval(self):
        if (
            self.notify_responsible
            and self.alarm_type not in self._get_responsible_aware_alarm_types()
        ):
            self.notify_responsible = False
        display_interval = self._interval_selection.get(self.interval, "")
        display_alarm_type = dict(
            self._fields["alarm_type"]._description_selection(self.env)
        ).get(self.alarm_type, "")
        self.name = "%s - %s %s" % (display_alarm_type, self.duration, display_interval)
        if self.notify_responsible:
            self.name += " - " + _("Notify Responsible")
