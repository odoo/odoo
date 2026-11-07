# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_im_status(self):
        super()._compute_im_status()
        for user in self.user_ids:
            dayfield = self.env['hr.employee']._get_current_day_location_field()
            # sudo: hr.employee.location - can read today's location of a user to show its IM status
            employee = user.sudo().employee_id
            location_type = (employee.exceptional_location_id or employee[dayfield]).location_type
            if not location_type:
                continue
            im_status = user.partner_id.im_status
            if im_status in ["online", "away", "busy", "offline"]:
                user.partner_id.im_status = location_type + "_" + im_status

