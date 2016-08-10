# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrExpenseConfigSettings(models.TransientModel):
    _name = 'hr.expense.config.settings'
    _inherit = 'res.config.settings'

    alias_expense_open = fields.Selection([
        ('open', "Accept expenses from any email address"),
        ('restricted', "Accept expenses from employee email addresses only")
        ], "Mail Gateway")

    alias_prefix = fields.Char('Default Alias Name for Expenses')
    alias_domain = fields.Char('Alias Domain', default=lambda self: self.env["ir.config_parameter"].get_param("mail.catchall.domain"))

    @api.model
    def get_default_alias_expense_open(self, fields):
        return {'alias_expense_open': self.env['ir.config_parameter'].get_param("hr_expense.email.gateway") or 'open'}

    @api.multi
    def set_default_alias_expense_open(self):
        self.env['ir.config_parameter'].set_param("hr_expense.email.gateway", self.alias_expense_open)
        return True

    @api.model
    def get_default_alias_prefix(self, fields):
        alias_name = self.env.ref('hr_expense.mail_alias_expense').alias_name
        return {'alias_prefix': alias_name}

    @api.multi
    def set_default_alias_prefix(self):
        for record in self:
            self.env.ref('hr_expense.mail_alias_expense').write({'alias_name': record.alias_prefix})
