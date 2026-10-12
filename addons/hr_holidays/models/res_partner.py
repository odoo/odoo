# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    leave_date_to = fields.Date(compute="_compute_leave_date_to")

    def _compute_leave_date_to(self):
        for partner in self:
            # in the rare case of multi-user partner, return the earliest
            # possible return date
            dates = partner.user_ids.mapped("leave_date_to")
            partner.leave_date_to = min(dates) if dates and all(dates) else False
