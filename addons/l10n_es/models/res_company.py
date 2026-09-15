from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )

    def _l10n_es_get_pos_edi_mode(self):
        """Return the POS EDI mode for this company.
        Returns 'tbai', 'verifactu', or False (standard session closing entry).
        """
        self.ensure_one()
        return False
