# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models, tools


class MailActivity(models.Model):
    _inherit = "mail.activity"

    phone = fields.Char("Phone", compute="_compute_phone_numbers", readonly=False, store=True)
    mobile = fields.Char("Mobile", compute="_compute_phone_numbers", readonly=False, store=True)

    @api.depends("res_model", "res_id", "activity_type_id")
    def _compute_phone_numbers(self):
        call_activities = self.filtered(
            lambda activity: activity.id
            and activity.res_model
            and activity.res_id
            and activity.activity_category == "phonecall"
        )
        (self - call_activities).phone = False
        (self - call_activities).mobile = False
        phone_numbers_by_activity = call_activities._get_phone_numbers_by_activity()
        for activity in call_activities:
            activity.mobile = phone_numbers_by_activity[activity]["mobile"]
            activity.phone = phone_numbers_by_activity[activity]["phone"]

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        call_activities = activities.filtered(
            lambda activity: (activity.phone or activity.mobile) and activity.activity_category == "phonecall"
        )
        notifications = [[user.partner_id, "refresh_call_activities", {}] for user in call_activities.user_id]
        self.env["bus.bus"]._sendmany(notifications)
        return activities

    def write(self, values):
        if "date_deadline" in values and self.user_id:
            self.env["bus.bus"]._sendmany(
                [[partner, "refresh_call_activities", {}] for partner in self.user_id.partner_id]
            )
        return super().write(values)

    @api.model
    def get_today_call_activities(self):
        """Retrieve the list of activities that:
          * have the type “phonecall”
          * have a phone number
          * are overdue
          * are assigned to the current user
          * are in the current company

        The resulting list is intended for display in the “Next Activities” tab.
        """
        overdue_call_activities_of_current_user = self.search(
            [
                ("activity_type_id.category", "=", "phonecall"),
                ("user_id", "=", self.env.uid),
                ("date_deadline", "<=", fields.Date.today()),
                "|",
                ("mobile", "!=", False),
                ("phone", "!=", False),
            ]
        )
        # ----- Tackling multi-company shenanigans 👺 -----
        record_ids_by_model_name = defaultdict(set)
        for activity in overdue_call_activities_of_current_user:
            record_ids_by_model_name[activity.res_model].add(activity.res_id)
        allowed_record_ids_by_model_name = defaultdict(list)
        for model_name, ids in record_ids_by_model_name.items():
            # calling search will filter out records that are irrelevant to the current company
            allowed_record_ids_by_model_name[model_name] = self.env[model_name].search([("id", "in", list(ids))]).ids
        return overdue_call_activities_of_current_user.filtered(
            lambda activity: activity.res_id in allowed_record_ids_by_model_name[activity.res_model]
        )._format_call_activities()

    def _action_done(self, feedback=False, attachment_ids=None):
        """Extends _action_done to notify the user assigned to a phonecall
        activity that it has been marked as done. This is useful to trigger the
        refresh of the “Next Activities” tab.
        """
        to_notify = self.filtered(
            lambda activity: activity.activity_type_id.category == "phonecall"
        ).user_id.partner_id
        self.env["bus.bus"]._sendmany([[partner, "refresh_call_activities", {}] for partner in to_notify])
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def _format_call_activities(self):
        """Serializes call activities for transmission to/use by the client side."""
        formatted_activities = []
        call_activities = self.filtered(lambda activity: activity.activity_type_id.category == "phonecall")
        for activity in call_activities:
            model = self.env[activity.res_model]
            record = model.browse(activity.res_id)
            activity_data = {
                **activity.read(["id", "res_name", "phone", "mobile", "res_id", "res_model", "state", "date_deadline", "mail_template_ids"])[0],
                "activity_category": activity.activity_type_id.category,
                "modelName": activity.sudo().res_model_id.display_name,
                "user_id": activity._read_format(["user_id"])[0]["user_id"],
            }
            partner = next(
                iter(record._mail_get_partners(introspect_fields=True)[record.id]),
                self.env["res.partner"],
            )
            if partner:
                activity_data["partner"] = partner.mail_partner_format()[partner]
            formatted_activities.append(activity_data)
        return formatted_activities

    def _get_phone_numbers_by_activity(self):
        """Batch compute the phone numbers associated with the activities.

        :return dict: for each activity, a sub-dict containing:
          * phone: phone number (obtained from the activity itself or from the related partner);
          * mobile: mobile number (obtained from the activity itself or from the related partner).
        """
        phone_numbers_by_activity = {}
        data_by_model = self._classify_by_model()
        for model, data in data_by_model.items():
            records = self.env[model].browse(data["record_ids"])
            for record, activity in zip(records, data["activities"]):
                mobile = record.mobile if "mobile" in record else False
                phone = record.phone if "phone" in record else False
                if not mobile and not phone:
                    recipient = next(
                        iter(record._mail_get_partners(introspect_fields=True)[record.id]),
                        self.env["res.partner"],
                    )
                    mobile = recipient.mobile
                    phone = recipient.phone
                phone_numbers_by_activity[activity] = {"mobile": mobile, "phone": phone}
        return phone_numbers_by_activity
