from odoo import fields, models

from .account_tax import REGIME_CODES_BY_USE, REGIME_CODES_IGIC_SALE_EXTRA


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )

    l10n_es_special_vat_regime = fields.Selection(
        selection=[
            ('cash_basis', 'Cash Basis'),
            ('equivalence_surcharge', 'Equivalence Surcharge'),
            ('reagyp', 'REAGYP'),
            ('simplified', 'Simplified'),
        ]
    )

    def _l10n_es_special_vat_regime_codes(self):
        self.ensure_one()
        return {
            'cash_basis': '07',
            'equivalence_surcharge': '18_iva',
            'reagyp': '19_iva',
            'simplified': '20',
        }

    def _l10n_es_regime_available_codes(self, use, applicability=None):
        """Return the codes valid for a given use ('sale'/'purchase') and tax applicability.

        Override gated behind the EDI's own boolean on this company, falling back to `super()` --
        keeps overrides order-independent when several EDI modules are installed together.
        """
        self.ensure_one()
        codes = REGIME_CODES_BY_USE.get(use, [])
        if use == 'sale' and applicability == '03':
            # '17' (OSS/IOSS) is an EU-only regime that doesn't exist in Canarias.
            codes = [code for code in codes if code != '17'] + REGIME_CODES_IGIC_SALE_EXTRA
        return codes

    def _l10n_es_get_pos_edi_mode(self):
        """Return the POS EDI mode for this company.
        Returns 'tbai', 'verifactu', or False (standard session closing entry).
        """
        self.ensure_one()
        return False
