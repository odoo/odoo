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

    def write(self, vals):
        res = super().write(vals)
        if 'state_id' in vals:
            for company in self.filtered(lambda c: c.account_fiscal_country_id.code == 'ES'):
                company._l10n_es_archive_taxes_by_state()
                company._l10n_es_apply_fiscal_positions_by_state()
        return res

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

    def _l10n_es_is_canary(self):
        self.ensure_one()
        return self.state_id.code in {'GC', 'TF'}

    def _l10n_es_archive_taxes_by_state(self):
        """For Canary companies, flip the CSV's mainland-oriented defaults:
        activate the IGIC taxes (l10n_es_applicability == '03', shipped inactive)
        and archive the mainland IVA taxes (shipped active).

        Non-Canary companies need no action: the CSV defaults already match
        (mainland active, IGIC inactive).

        Taxes without `l10n_es_applicability` set (withholdings/IRPF, common
        to both regimes) are left untouched.
        """
        self.ensure_one()
        ChartTemplate = self.env['account.chart.template'].with_company(self)
        if self.account_fiscal_country_id.code != 'ES' or not self.state_id:
            return

        regime_taxes = self.env['account.tax'].with_context(active_test=False).search([
            *self.env['account.tax']._check_company_domain(self),
            ('country_id.code', '=', 'ES'),
            ('l10n_es_applicability', '!=', False)
        ])

        canary_taxes = regime_taxes.filtered(
            lambda t: t.l10n_es_applicability == '03'
        )
        mainland_taxes = regime_taxes - canary_taxes

        is_canary = self._l10n_es_is_canary()
        canary_taxes.active = is_canary
        mainland_taxes.active = not is_canary

        sale_tax_xml_id = 'account_tax_template_igic_r_7' if is_canary else 'account_tax_template_s_iva21b'
        purchase_tax_xml_id = 'account_tax_template_igic_sop_7' if is_canary else 'account_tax_template_p_iva21_bc'

        sale_tax = ChartTemplate.ref(sale_tax_xml_id, raise_if_not_found=False)
        purchase_tax = ChartTemplate.ref(purchase_tax_xml_id, raise_if_not_found=False)

        if sale_tax:
            self.account_sale_tax_id = sale_tax
        if purchase_tax:
            self.account_purchase_tax_id = purchase_tax

    def _l10n_es_apply_fiscal_positions_by_state(self):
        """Toggle auto_apply on the mainland/Canary fiscal positions to match
        the company's current state"""

        self.ensure_one()
        ChartTemplate = self.env['account.chart.template'].with_company(self)
        mainland_fp_xml_ids = (
            'l10n_es_domestic_fiscal_position',
            'fp_intra_private',
            'fp_intra',
            'fp_extra',
        )
        canary_fp_xml_ids = (
            'fp_canary_1',
            'fp_extra_canary',
        )
        is_canary = self._l10n_es_is_canary()
        for xml_id in mainland_fp_xml_ids:
            fp = ChartTemplate.ref(xml_id, raise_if_not_found=False)
            if fp:
                fp.auto_apply = not is_canary
        for xml_id in canary_fp_xml_ids:
            fp = ChartTemplate.ref(xml_id, raise_if_not_found=False)
            if fp:
                fp.auto_apply = is_canary
