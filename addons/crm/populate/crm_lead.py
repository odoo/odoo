# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = "crm.lead"
    _populate_sizes = {"small": 500, "medium": 5_000, "large": 50_000}
    _populate_dependencies = ['res.users']

    def _populate_factories(self):
        user_ids = self.env.registry.populated_models['res.users']
        return [
            ("name", populate.constant('Lead #{counter}')),
            ("active", populate.randomize([True, False], [0.5, 0.5])),
            ("user_id", populate.randomize(user_ids))
        ]

    def _populate(self, size):
        records = super()._populate(size)

        activity_types = self.env["ir.model.data"].search([("model", "=", "mail.activity.type")]).mapped("complete_name")
        random = populate.Random("random activity type")
        for r in records:
            act_type_xmlid = random.choices(activity_types)[0]
            r.activity_schedule(act_type_xmlid)
            r.activity_feedback([act_type_xmlid])

        return records
