# -*- coding: utf-8 -*-

from odoo import api, models


class SwissSetupBarBankConfigWizard(models.TransientModel):
    _inherit = 'account.setup.bank.manual.config'

    @api.onchange('acc_number')
    def _onchange_recompute_qr_iban(self):
        # Needed because ORM doesn't properly call the compute in 'new' mode, due to inherits, and
        # we want this field to be displayed in the wizard. We need to manually set acc_number
        # on the inherits m2o before calling the compute function manually.
        self.res_partner_bank_id.acc_number = self.acc_number
        self.res_partner_bank_id._compute_l10n_ch_qr_iban()
        self.l10n_ch_qr_iban = self.res_partner_bank_id.l10n_ch_qr_iban
