# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class ResCompany(models.Model):

    _inherit = "res.company"

    l10n_nl_reports_sbr_ob_nummer = fields.Char('Omzetbelastingnummer', help="This number is used for contacts with the Tax Administration.")

    def _get_nl_vat(self):
        if self.country_code == 'NL' and self.l10n_nl_reports_sbr_ob_nummer:
            return self.l10n_nl_reports_sbr_ob_nummer

        return super()._get_nl_vat()
