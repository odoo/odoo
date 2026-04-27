# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class SaftImportWizard(models.TransientModel):
    """ SAF-T import wizard to import DK specific files """
    _inherit = 'account.saft.import.wizard'

    def _get_account_types(self):
        """ Returns a mapping between the account types accepted for the SAF-T and the types in Odoo """
        # Overrides
        if self.company_id.country_code != 'DK':
            return super()._get_account_types()
        return {
            'Asset': 'asset_current',
            'Liability': 'liability_current',
            'Sale': 'income',
            'Expense': 'expense',
            'Other': 'off_balance',
        }
