# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_alias_prefix = fields.Char('Default Alias Name for Expenses', compute='_compute_expense_alias_prefix',
        store=True, readonly=False)
    use_mailgateway = fields.Boolean(string='Let your employees record expenses by email',
                                     config_parameter='hr_expense.use_mailgateway')

    module_hr_payroll_expense = fields.Boolean(string='Reimburse Expenses in Payslip')
    module_hr_expense_extract = fields.Boolean(string='Send bills to OCR to generate expenses')


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            expense_alias_prefix=self.env.ref('hr_expense.mail_alias_expense').alias_name,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env.ref('hr_expense.mail_alias_expense').write({'alias_name': self.expense_alias_prefix})

    @api.depends('use_mailgateway')
    def _compute_expense_alias_prefix(self):
        self.filtered(lambda w: not w.use_mailgateway).update({'expense_alias_prefix': False})
