# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    leave_date_to = fields.Date(compute="_compute_leave_date_to")

    def _compute_leave_date_to(self):
        for partner in self:
            # in the rare case of multi-user partner, return the earliest
            # possible return date
            dates = partner.user_ids.mapped("leave_date_to")
            partner.leave_date_to = min(dates) if dates and all(dates) else False

    @api.model
    def _get_inactive_partners_data(self):
        inactive_partner_ids = super()._get_inactive_partners_data()
        absent_employees = self.env["hr.employee"].search_fetch([
            ("user_id", "in", {p["user_id"] for p in inactive_partner_ids if p["user_id"]}),
            ("is_absent", "=", True),
        ])
        # return only partners with employees that are not absent (holiday, sick leave, etc.)
        # This avoids sending notifications to users that are on leave
        return [
            p
            for p in inactive_partner_ids
            if p["user_id"] not in absent_employees.user_id.ids
        ]
