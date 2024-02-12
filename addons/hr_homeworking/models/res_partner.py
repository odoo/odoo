# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_im_status(self):
        super()._compute_im_status()
        dayfield = self.env['hr.employee']._get_current_day_location_field()
        for partner in self:
            location_type = self.employee_id[dayfield].location_type
            if not location_type:
                continue
            im_status = partner.im_status
            if im_status == "online" or im_status == "away" or im_status == "offline":
                partner.im_status = location_type + "_" + im_status

    def get_worklocation(self, start_date, end_date):
        return self.employee_id._get_worklocation(start_date, end_date)
