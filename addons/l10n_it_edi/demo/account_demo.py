# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _l10n_it_edi_set_demo_data(self):
        """Set EDI fields on l10n_it demo partners"""
        edi_data = {
            'IT01234560157': {'l10n_it_codice_fiscale': '01234560157', 'l10n_it_pa_index': 'M5UXCR1'},
            'IT01199250158': {'l10n_it_codice_fiscale': '01199250158', 'l10n_it_pa_index': 'UFJ9DC'},
        }
        for vat, vals in edi_data.items():
            partner = self.search([('vat', '=', vat)], limit=1)
            if partner:
                partner.write(vals)

        partner = self.search([('email', '=', 'mario.rossi@email.it')], limit=1)
        if partner:
            partner.write({'l10n_it_codice_fiscale': 'RSSMRA80A01F205X'})
