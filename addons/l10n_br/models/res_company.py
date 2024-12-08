# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # ==== Business fields ====
    l10n_br_ie_code = fields.Char(string="IE", related="partner_id.l10n_br_ie_code", readonly=False)  # each state has its own format. Not all of the validation rules can be easily found.
    l10n_br_im_code = fields.Char(string="IM", related="partner_id.l10n_br_im_code", readonly=False)  # each municipality has its own format. There is no information about validation anywhere.
    l10n_br_nire_code = fields.Char(string="NIRE", help="State Commercial Identification Number. Should contain 11 digits.")

    def _localization_use_documents(self):
        self.ensure_one()
        return self.account_fiscal_country_id.code == "BR" or super()._localization_use_documents()

    def _is_latam(self):
        return super()._is_latam() or self.account_fiscal_country_id.code == 'BR'
