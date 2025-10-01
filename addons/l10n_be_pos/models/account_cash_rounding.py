from odoo import api, models


class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    @api.model
    def _setup_default_rounding_method(self):
        xml_id = 'l10n_be_pos.cash_rounding_be_05'

        rounding_method = self.env.ref(xml_id, raise_if_not_found=False)

        if rounding_method:
            return

        rounding_method = self.env['account.cash.rounding'].search([
            ('rounding', '=', 0.05),
            ('rounding_method', '=', 'HALF-UP'),
            ('strategy', '=', 'add_invoice_line'),
        ], limit=1)

        if not rounding_method:
            profit_account = self.env['account.account'].search([
                ('code', '=', '743000'),
            ], limit=1)
            loss_account = self.env['account.account'].search([
                ('code', '=', '643000'),
            ], limit=1)
            rounding_method = self.env['account.cash.rounding'].create({
                'name': 'Round to 0.05',
                'rounding': 0.05,
                'strategy': 'add_invoice_line',
                'rounding_method': 'HALF-UP',
                'profit_account_id': profit_account.id,
                'loss_account_id': loss_account.id,
            })

        self.env['ir.model.data']._update_xmlids([{
            'xml_id': xml_id,
            'record': rounding_method,
        }])
