# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class VoipQueueMixin(models.AbstractModel):
    _name = "voip.queue.mixin"
    _description = "VOIP Queue support"

    has_call_in_queue = fields.Boolean("Is in the Call Queue", compute="_compute_has_call_in_queue")

    def _compute_has_call_in_queue(self):
        activity_count_by_res_id = dict(
            self.env["mail.activity"]._read_group(
                [
                    ("res_id", "in", self.ids),
                    ("res_model", "=", self._name),
                    ("user_id", "=", self.env.uid),
                    ("activity_type_id.category", "=", "phonecall"),
                    ("date_deadline", "<=", fields.Date.today()),
                    "|",
                    ("phone", "!=", False),
                    ("mobile", "!=", False),
                ],
                ["res_id"],
                ["__count"],
            )
        )
        for record in self:
            record.has_call_in_queue = activity_count_by_res_id.get(record.id, 0) > 0

    def create_call_activity(self):
        if not self:
            return self.env["mail.activity"]
        # Ensure that a phonecall activity type exists beforehand, otherwise
        # create one. This is important because we rely on this type to retrieve
        # the activities to be displayed in the Next Activities tab.
        phonecall_activity_type_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.mail_activity_data_call", raise_if_not_found=False
        )
        if not phonecall_activity_type_id:
            phonecall_activity_type_id = (
                self.env["mail.activity.type"]
                .search(
                    [
                        "|",
                        ("res_model", "=", False),
                        ("res_model", "=", self._name),
                        ("category", "=", "phonecall"),
                    ],
                    limit=1,
                )
                .id
            )
        if not phonecall_activity_type_id:
            phonecall_activity_type_id = (
                self.env["mail.activity.type"]
                .sudo()
                .create(
                    {
                        "category": "phonecall",
                        "delay_count": 2,
                        "icon": "fa-phone",
                        "name": _("Call"),
                        "sequence": 999,
                    }
                )
                .id
            )
        date_deadline = fields.Date.today(self)
        res_model_id = self.env["ir.model"]._get_id(self._name)
        activities = self.env["mail.activity"].create(
            [
                {
                    "activity_type_id": phonecall_activity_type_id,
                    "date_deadline": date_deadline,
                    "res_id": record.id,
                    "res_model_id": res_model_id,
                    "user_id": self.env.uid,
                }
                for record in self
            ]
        )
        failed_activities = activities.filtered(lambda activity: not activity.mobile and not activity.phone)
        if failed_activities:
            failed_records = self.browse(failed_activities.mapped("res_id"))
            raise UserError(
                _(
                    "Some documents cannot be added to the call queue as they do not have a phone number set: %(record_names)s",
                    record_names=_(", ").join(failed_records.mapped("display_name")),
                )
            )
        return activities

    @api.model
    def delete_call_activity(self, res_id):
        related_activities = self.env["mail.activity"].search(
            [
                ("res_id", "=", res_id),
                ("res_model", "=", self._name),
                ("user_id", "=", self.env.uid),
                ("activity_type_id.category", "=", "phonecall"),
                ("date_deadline", "<=", fields.Date.today()),
                "|",
                ("phone", "!=", False),
                ("mobile", "!=", False),
            ]
        )
        self.env["bus.bus"]._sendmany(
            [
                [self.env.user.partner_id, "delete_call_activity", {"id": activity.id}]
                for activity in related_activities
            ]
        )
        related_activities.unlink()
