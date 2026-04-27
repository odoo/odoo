# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrCandidate(models.Model):
    _inherit = 'hr.candidate'

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        request_ids = self.env['sign.request.item'].search([
            ('partner_id', '=', self.partner_id.id)]).sign_request_id
        vals['sign_request_ids'] = request_ids.ids
        return vals
