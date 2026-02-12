from odoo import models

NILVERA_TEST_VAT_NUMS = {'1234567801', '1234567802'}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def check_vat_tr(self, vat):
        # EXTENDS 'base_vat'
        company = self.env.company
        return super().check_vat_tr(vat) or (company.l10n_tr_nilvera_use_test_env and vat in NILVERA_TEST_VAT_NUMS)
