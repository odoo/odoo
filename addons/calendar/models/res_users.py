import datetime
from datetime import UTC

from odoo import _, api, fields, models, modules
from odoo.exceptions import AccessError
from odoo.libs.datetime import timezone
from odoo.tools import SQL


class ResUsers(models.Model):
    _inherit = "res.users"

    calendar_default_privacy = fields.Selection(
        selection=[
            ("public", "Public by default"),
            ("private", "Private by default"),
            ("confidential", "Internal users only"),
        ],
        compute="_compute_calendar_default_privacy",
        inverse="_inverse_calendar_default_privacy",
    )

    def _get_calendar_event_resource(self):
        self.check_singleton()
        return self._get_calendar_event_resources()[self]

    def _get_calendar_event_resources(self):
        """Resolve people through their party, one query per company represented."""
        resources = {}
        for company, users in self.grouped("company_id").items():
            by_partner = users.partner_id._get_calendar_event_resources(company)
            resources.update({user: by_partner[user.partner_id] for user in users})
        return resources

    def _get_or_create_calendar_event_resource(self):
        self.check_singleton()
        self.env.cr.execute(
            SQL(
                "UPDATE res_users SET write_date = write_date WHERE id = %s",
                self.id,
            )
        )
        resource = self._get_calendar_event_resource()
        if not resource:
            resource = (
                self.env["resource.resource"]
                .sudo()
                .create(
                    {
                        "name": self.name,
                        "user_id": self.id,
                        "company_id": self.company_id.id,
                        "tz": self.tz or "UTC",
                    }
                )
            )
            self.env["calendar.event"].sudo().search(
                [
                    ("partner_ids", "in", self.partner_id.ids),
                ]
            )._sync_reservations()
        resource._lock_for_scheduling()
        return resource

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["calendar_default_privacy"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["calendar_default_privacy"]

    def get_selected_calendars_partner_ids(self, include_user=True):
        self.check_singleton()
        partner_ids = (
            self.env["calendar.filters"]
            .search([("user_id", "=", self.id), ("partner_checked", "=", True)])
            .partner_id.ids
        )

        if include_user:
            partner_ids += [self.partner_id.id]
        return partner_ids

    @api.model
    def _get_user_calendar_default_privacy(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("calendar.default_privacy", "public")
        )

    @api.model_create_multi
    def create(self, vals_list):
        default_privacy = self._get_user_calendar_default_privacy()
        for vals_dict in vals_list:
            if not vals_dict.get("calendar_default_privacy"):
                vals_dict.update(calendar_default_privacy=default_privacy)

        return super().create(vals_list)

    def write(self, vals):
        privacy_update = "calendar_default_privacy" in vals
        if privacy_update and self != self.env.user:
            raise AccessError(
                _(
                    "You are not allowed to change the calendar default privacy of another user due to privacy constraints."
                )
            )
        result = super().write(vals)
        if "tz" in vals or "company_id" in vals:
            self.env["calendar.event"].sudo().search(
                [
                    ("partner_ids", "in", self.partner_id.ids),
                ]
            )._sync_reservations()
        return result

    @api.depends("res_users_settings_id.calendar_default_privacy")
    def _compute_calendar_default_privacy(self):
        fallback_default_privacy = "public"
        if any(
            not user.sudo().res_users_settings_id.calendar_default_privacy
            for user in self
        ):
            fallback_default_privacy = self._get_user_calendar_default_privacy()

        for user in self:
            user.calendar_default_privacy = (
                user.sudo().res_users_settings_id.calendar_default_privacy
                or fallback_default_privacy
            )

    def _inverse_calendar_default_privacy(self):
        for user in self.filtered(lambda user: user._is_internal()):
            settings = (
                self.env["res.users.settings"].sudo()._get_or_create_for_user(user)
            )
            configuration = {
                field: user[field]
                for field in self._get_fields_user_calendar_configuration()
            }
            settings.sudo().update(configuration)

    @api.model
    def _get_fields_user_calendar_configuration(self) -> list[str]:
        return ["calendar_default_privacy"]

    def _systray_get_calendar_event_domain(self):
        start_dt_utc = start_dt = datetime.datetime.now(UTC)
        stop_dt_utc = datetime.datetime.combine(
            start_dt_utc.date(), datetime.time.max
        ).replace(tzinfo=UTC)

        tz = self.env.user.tz
        if tz:
            user_tz = timezone(tz)
            start_dt = start_dt_utc.astimezone(user_tz)
            stop_dt = datetime.datetime.combine(
                start_dt.date(), datetime.time.max
            ).replace(tzinfo=user_tz)
            stop_dt_utc = stop_dt.astimezone(UTC)

        start_date = start_dt.date()

        current_user_non_declined_attendee_ids = self.env["calendar.attendee"]._search(
            [
                ("partner_id", "=", self.env.user.partner_id.id),
                ("state", "!=", "declined"),
            ]
        )

        return [
            "&",
            "|",
            "&",
            "|",
            ["start", ">=", fields.Datetime.to_string(start_dt_utc)],
            ["stop", ">=", fields.Datetime.to_string(start_dt_utc)],
            ["start", "<=", fields.Datetime.to_string(stop_dt_utc)],
            "&",
            ["allday", "=", True],
            ["start_date", "=", fields.Date.to_string(start_date)],
            ("attendee_ids", "in", current_user_non_declined_attendee_ids),
        ]

    @api.model
    def _get_activity_groups(self):
        res = super()._get_activity_groups()
        EventModel = self.env["calendar.event"]
        meetings_lines = EventModel.search_read(
            self._systray_get_calendar_event_domain(),
            ["id", "start", "name", "allday"],
            order="start",
        )
        if meetings_lines:
            meeting_label = _("Today's Meetings")
            meetings_systray = {
                "id": self.env["ir.model"]._get("calendar.event").id,
                "type": "meeting",
                "name": meeting_label,
                "model": "calendar.event",
                "icon": modules.module.get_module_icon_path(
                    EventModel._original_module
                ),
                "domain": [("active", "in", [True, False])],
                "meetings": meetings_lines,
                "view_type": EventModel._systray_view,
            }
            res.insert(0, meetings_systray)
        return res

    @api.model
    def check_calendar_credentials(self):
        return {}

    def check_synchronization_status(self):
        return {}

    def _has_any_active_synchronization(self):
        return False
