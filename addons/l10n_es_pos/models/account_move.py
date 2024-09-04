# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_l10n_es_is_simplified(self):
        super()._compute_l10n_es_is_simplified()
        for move in self:
            if move.pos_order_ids:
                move.l10n_es_is_simplified = move.pos_order_ids[0].is_l10n_es_simplified_invoice

    def _generate_pdf_and_send_invoice(self, template, force_synchronous=True, allow_fallback_pdf=True, bypass_download=False, **kwargs):
        if self.company_id.country_code == "ES" and not self.company_id.l10n_es_edi_facturae_certificate_id:
            kwargs['l10n_es_edi_facturae_checkbox_xml'] = False
        return super()._generate_pdf_and_send_invoice(template, force_synchronous, allow_fallback_pdf, bypass_download, **kwargs)
