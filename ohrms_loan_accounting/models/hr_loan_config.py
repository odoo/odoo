from odoo import models, fields, api, _


class AccConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    loan_approve = fields.Boolean(default=False, string="Approval from Accounting Department",
                                  help="Loan Approval from account manager")

    @api.model
    def get_values(self):
        res = super(AccConfig, self).get_values()
        res.update(
            loan_approve=self.env['ir.config_parameter'].sudo().get_param('account.loan_approve')
        )
        return res

    
    def set_values(self):
        super(AccConfig, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('account.loan_approve', self.loan_approve)

