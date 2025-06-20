# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = 'res.partner'

    leave_date_to = fields.Date(compute="_compute_leave_date_to")

    def _compute_leave_date_to(self):
        for partner in self:
            # in the rare case of multi-user partner, return the earliest
            # possible return date
            dates = partner.user_ids.mapped("leave_date_to")
            partner.leave_date_to = min(dates) if dates and all(dates) else False

    def _to_store_defaults(self):
        return super()._to_store_defaults() + [
            Store.One(
                "main_user_id",
                [Store.Attr("leave_date_to", lambda u: u.leave_date_to if u.active else False)],
            ),
        ]
