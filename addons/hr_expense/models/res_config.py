# -*- coding: utf-8 -*-

from odoo import api, fields, models

class HrExpenseConfigSettings(models.TransientModel):
    _name = 'hr.expense.config.settings'
    _inherit = 'res.config.settings'

    alias_prefix = fields.Char('Default Alias Name for Expenses')
    alias_domain = fields.Char('Alias Domain', default=lambda self: self.env["ir.config_parameter"].get_param("mail.catchall.domain"))

    @api.model
    def get_default_alias_prefix(self, fields):
        alias_name = self.env.ref('hr_expense.mail_alias_expense').alias_name
        return {'alias_prefix': alias_name}

    @api.multi
    def set_default_alias_prefix(self):
        for record in self:
            self.env.ref('hr_expense.mail_alias_expense').write({'alias_name': record.alias_prefix})
