# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def _get_default_send_hr_documents_access_link(self):
        employee = self.env['hr.employee'].browse(self.env.context.get('active_id'))
        return self.env.company.documents_hr_settings and self.env.company.documents_hr_folder and employee.private_email

    send_hr_documents_access_link = fields.Boolean(
        string="Send Access Link",
        default=_get_default_send_hr_documents_access_link,
        help="Send a share link to the private email of the employee with all the HR files he owns in Documents app")

    private_email = fields.Char(related="employee_id.private_email", readonly=False)

    def action_register_departure(self):
        super().action_register_departure()
        if self.send_hr_documents_access_link:
            self.employee_id.action_send_documents_share_link()
