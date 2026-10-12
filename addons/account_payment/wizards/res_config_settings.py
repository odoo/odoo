# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pay_invoices_online = fields.Boolean(config_parameter='account_payment.enable_portal_payment')

    # Intercompany clearing
    account_interco_clearing_journal_id = fields.Many2one(
        comodel_name='account.journal',
        readonly=False,
        check_company=True,
        related='company_id.account_interco_clearing_journal_id',
    )
    account_interco_payable_id = fields.Many2one(
        comodel_name='account.account',
        readonly=False,
        check_company=True,
        related='company_id.account_interco_payable_id',
    )
    account_interco_receivable_id = fields.Many2one(
        comodel_name='account.account',
        readonly=False,
        check_company=True,
        related='company_id.account_interco_receivable_id',
    )

    @api.onchange('pay_invoices_online')
    def _onchange_pay_invoices_online(self):
        if not self.pay_invoices_online:
            self.link_qr_code = False
