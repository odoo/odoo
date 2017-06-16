# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrExpenseConfigSettings(models.TransientModel):
    _name = 'hr.expense.config.settings'
    _inherit = 'res.config.settings'

    alias_prefix = fields.Char('Default Alias Name for Expenses')
    alias_domain = fields.Char('Alias Domain', default=lambda self: self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain"))
    group_analytic_accounting = fields.Boolean(
        string='Analytic Accounting',
        implied_group='analytic.group_analytic_accounting')
    group_uom = fields.Boolean(
        string="Units of Measure",
        implied_group='product.group_uom')
    use_mailgateway = fields.Boolean(string='Let your employees record expenses by email')
    module_project = fields.Boolean(string="Project")
    module_sale = fields.Boolean(string="Customer Billing")

    @api.model
    def get_values(self):
        res = super(HrExpenseConfigSettings, self).get_values()
        res.update(
            alias_prefix=self.env.ref('hr_expense.mail_alias_expense').alias_name,
            use_mailgateway=self.env['ir.config_parameter'].sudo().get_param('hr_expense.use_mailgateway'),
        )
        return res

    @api.multi
    def set_values(self):
        super(HrExpenseConfigSettings, self).set_values()
        self.env.ref('hr_expense.mail_alias_expense').write({'alias_name': self.alias_prefix})
        self.env['ir.config_parameter'].sudo().set_param('hr_expense.use_mailgateway', self.use_mailgateway)

    @api.onchange('use_mailgateway')
    def _onchange_use_mailgateway(self):
        if not self.use_mailgateway:
            self.alias_prefix = False
