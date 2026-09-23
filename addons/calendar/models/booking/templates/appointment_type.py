from odoo import Command, _, api, models


class AppointmentType(models.Model):
    """Template-driven setup helpers for appointment.type, used by onboarding and the kanban helper."""

    _inherit = "appointment.type"

    @api.model
    def action_setup_appointment_type_template(self, template_key):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "calendar.appointment_type_action"
        )
        template_values = self._get_appointment_type_template_values(template_key)
        action["res_id"] = self.env["appointment.type"].create(template_values).id
        action["views"] = [
            [self.env.ref("calendar.appointment_type_view_form").id, "form"]
        ]
        return action

    @api.model
    def get_appointment_type_templates_data(self):
        """
        Returns onboarding template names and all linked necessary rendering information.
        """
        return {
            "meeting": {
                "description": _("Let others book a meeting in your calendar"),
                "icon": "/calendar/static/src/booking/img/guy.svg",
                "template_key": "meeting",
                "title": _("Meeting"),
            },
            "video_call": {
                "description": _(
                    "Schedule a video meeting in a virtual room with one or more participants"
                ),
                "icon": "/calendar/static/src/booking/img/headset.svg",
                "template_key": "video_call",
                "title": _("Video Call"),
            },
            "table_booking": {
                "description": _(
                    "Let customers book a table in your restaurant or bar"
                ),
                "icon": "/calendar/static/src/booking/img/foods.svg",
                "template_key": "table_booking",
                "title": _("Table Booking"),
            },
            "book_resource": {
                "description": _(
                    "Let customers book a resource such as a room, a tennis court, etc."
                ),
                "icon": "/calendar/static/src/booking/img/clock.svg",
                "template_key": "book_resource",
                "title": _("Book a Resource"),
            },
        }

    def _get_appointment_type_template_values(self, template_key):
        if template_key == "meeting":
            return self._prepare_meeting_template_values()
        elif template_key == "video_call":
            return self._prepare_video_call_template_values()
        elif template_key == "table_booking":
            return self._prepare_table_booking_template_values()
        elif template_key == "book_resource":
            return self._prepare_book_resource_template_values()
        return {}

    @api.model
    def _prepare_meeting_template_values(self):
        return {
            "name": _("Meeting"),
            "appointment_duration": 1.0,
            "is_auto_assign": False,
            "is_date_first": False,
            "event_videocall_source": False,
            "show_avatars": True,
            "staff_user_ids": [Command.set([self.env.user.id])],
        }

    @api.model
    def _prepare_video_call_template_values(self):
        return {
            "allow_guests": True,
            "appointment_duration": 0.5,
            "slot_creation_interval": 0.5,
            "is_auto_assign": False,
            "is_date_first": False,
            "location_id": False,
            "name": _("Video Call"),
            "question_ids": [
                Command.create(
                    {
                        "title": _("Describe what you need"),
                        "question_type": "text_box",
                    }
                )
            ],
            "show_avatars": False,
        }

    @api.model
    def _prepare_table_booking_template_values(self):
        return {
            "appointment_duration": 2.0,
            "slot_creation_interval": 0.5,
            "is_auto_assign": True,
            "event_videocall_source": False,
            "hide_duration": True,
            "location_id": self.env.company.partner_id.id,
            "min_cancellation_hours": 1,
            "max_schedule_days": 45,
            "min_schedule_hours": 1.0,
            "name": _("Table"),
            "question_ids": [
                Command.create(
                    {
                        "title": _(
                            "Do you have any dietary preferences or restrictions ?"
                        ),
                        "question_placeholder": _(
                            "e.g. Vegetarian, Lactose Intolerant, ..."
                        ),
                        "question_type": "text_box",
                    }
                )
            ],
            "resource_ids": [
                Command.create(
                    {
                        "name": _("Table %s", number),
                        "capacity": capacity,
                    }
                )
                for number, capacity in enumerate([2, 2, 4, 6], start=1)
            ],
            "manage_capacity": True,
            "slot_ids": [
                Command.create(
                    {
                        "weekday": str(weekday),
                        "start_hour": start_hour,
                        "end_hour": end_hour,
                    }
                )
                for (start_hour, end_hour) in [(12, 14.5), (19, 0)]
                for weekday in range(2, 7)
            ],
            "schedule_based_on": "resources",
            "staff_user_ids": [],
        }

    @api.model
    def _prepare_book_resource_template_values(self):
        return {
            "allow_guests": True,
            "appointment_duration": 1.0,
            "event_videocall_source": False,
            "is_auto_assign": False,
            "is_date_first": True,
            "location_id": self.env.company.partner_id.id,
            "min_cancellation_hours": 1,
            "max_schedule_days": 45,
            "min_schedule_hours": 1.0,
            "name": _("Book a Resource"),
            "resource_ids": [
                Command.create(
                    {
                        "name": _("Resource %s", number),
                    }
                )
                for number in range(1, 5)
            ],
            "schedule_based_on": "resources",
            "staff_user_ids": [],
        }
