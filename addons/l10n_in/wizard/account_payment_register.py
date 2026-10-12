# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.company.account_fiscal_country_id.code == 'IN' and 'withhold' in fields_list:
            active_model = self.env.context.get('active_model')
            active_ids = self.env.context.get('active_ids', [])
            move_count = 0
            if active_model == 'account.move':
                move_count = len(active_ids)
            elif active_model == 'account.move.line':
                move_count = len(self.env['account.move.line'].browse(active_ids).mapped('move_id'))
            # In India, hide withholding options for group payments and use "Withhold" instead of "Withhold and Pay" for individual payments.
            if move_count > 1:
                res['withhold'] = 'payment'
            elif res['withhold'] == 'withhold_pay':
                res['withhold'] = 'withhold'
        return res

    @api.depends('withhold')
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for wizard in self:
            if wizard.company_id.account_fiscal_country_id.code == 'IN' and wizard.withhold == 'withhold' and wizard.company_id.l10n_in_withholding_journal_id:
                wizard.journal_id = wizard.company_id.l10n_in_withholding_journal_id
