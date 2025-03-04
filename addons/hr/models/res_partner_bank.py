# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_street = fields.Char(related='bank_id.street', readonly=False)
    bank_street2 = fields.Char(related='bank_id.street2', readonly=False)
    bank_zip = fields.Char(related='bank_id.zip', readonly=False)
    bank_city = fields.Char(related='bank_id.city', readonly=False)
    bank_state = fields.Many2one(related='bank_id.state', readonly=False)
    bank_country = fields.Many2one(related='bank_id.country', readonly=False)
    bank_email = fields.Char(related='bank_id.email', readonly=False)
    bank_phone = fields.Char(related='bank_id.phone', readonly=False)
    employee_id = fields.Many2one('hr.employee', 'Employee', compute="_compute_employee_id")

    @api.depends('partner_id')
    def _compute_employee_id(self):
        for bank in self:
            if bank.partner_id.employee:
                bank.employee_id = bank.partner_id.employee_ids.filtered(lambda e: e.company_id in self.env.companies)[:1]
            else:
                bank.employee_id = False

    def _compute_display_name(self):
        account_employee = self.browse()
        if not self.env.user.has_group('hr.group_hr_user'):
            account_employee = self.sudo().filtered("partner_id.employee_ids")
            for account in account_employee:
                account.sudo(self.env.su).display_name = \
                    account.acc_number[:2] + "*" * len(account.acc_number[2:-4]) + account.acc_number[-4:]
        super(ResPartnerBank, self - account_employee)._compute_display_name()
