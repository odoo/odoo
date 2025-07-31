from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_es_is_foreign(self):
        self.ensure_one()

        return self.country_id.code not in ('ES', False) or (self.vat or '').startswith("ESN")

    def _l10n_es_is_legal_entity(self):
        """
        Determines if the Spanish VAT corresponds to a legal entity (CIF format):
        CIF = 1 letter + 8 digits (e.g., A12345678)
        """
        vat = (self.vat or '').upper()
        if not vat.startswith("ES") or len(vat) != 11:
            return False

        core = vat[2:]  # Strip 'ES'
        return core[0].isalpha() and core[1:].isdigit()
