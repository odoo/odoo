# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    alias_prefix = fields.Char('Default Alias Name for Expenses')
    alias_domain = fields.Char('Alias Domain', default=lambda self: self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain"))
    use_mailgateway = fields.Boolean(string='Let your employees record expenses by email')
    module_sale = fields.Boolean(string="Customer Billing")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            alias_prefix=self.env.ref('hr_expense.mail_alias_expense').alias_name,
            use_mailgateway=self.env['ir.config_parameter'].sudo().get_param('hr_expense.use_mailgateway'),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env.ref('hr_expense.mail_alias_expense').write({'alias_name': self.alias_prefix})
        self.env['ir.config_parameter'].sudo().set_param('hr_expense.use_mailgateway', self.use_mailgateway)

    @api.onchange('use_mailgateway')
    def _onchange_use_mailgateway(self):
        if not self.use_mailgateway:
            self.alias_prefix = False
