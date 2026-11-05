from odoo import models

# Column of the Azerbaijani electronic invoice (EQF) in which the lines are reported, per tax group of the chart.
EQF_VAT_TYPE_PER_TAX_GROUP = {
    'az_tax_group_vat_18': 'taxable',
    'az_tax_group_vat_20': 'taxable',
    'az_tax_group_vat_0': 'zero_rated',
    'az_tax_group_vat_exempt': 'exempt',
    'az_tax_group_out_of_scope': 'non_vat',
}


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_az_eqf_get_vat_type(self):
        """ EQF VAT treatment of the tax ('taxable', 'zero_rated', 'exempt' or 'non_vat'), given by its tax group.

        :return: the treatment, or False when the tax group is not reported on the EQF.
        """
        self.ensure_one()
        # Tax groups created from the chart template are named 'account.<company_id>_<template xmlid>'.
        xmlid = self.tax_group_id.get_external_id()[self.tax_group_id.id]
        return EQF_VAT_TYPE_PER_TAX_GROUP.get(xmlid.partition('_')[2], False)
