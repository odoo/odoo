# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

# Default catalog for a company with no EDI enabled; each EDI adds its own codes through its
# override of `_l10n_es_regime_available_codes`.
REGIME_CODES_BY_USE = {
    'sale': [
        '01', '03', '04', '05', '07', '08',
        '02_sale', '09_sale', '12_sale', '13_sale',
        '10', '11', '14_sale', '15', '17',
    ],
    'purchase': [
        '01', '03', '04', '05', '07', '08',
        '02_purchase', '09_purchase', '12_purchase', '13_purchase'
    ],
}

# Added to the sale catalog when the tax applicability is IGIC ('03'). Suffixed `_sale`
# because the IGIC purchase codes are numbered differently (17 on sales == 15 on purchases).
REGIME_CODES_IGIC_SALE_EXTRA = ['17_igic_sale', '18_igic_sale', '19_igic_sale']


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_es_exempt_reason = fields.Selection(
        selection=[
            ('E1', 'Art. 20'),
            ('E2', 'Art. 21'),
            ('E3', 'Art. 22'),
            ('E4', 'Art. 23 y 24'),
            ('E5', 'Art. 25'),
            ('E6', 'Otros'),
        ],
        string="Exempt Reason (Spain)",
    )
    l10n_es_type = fields.Selection(
        selection=[
            ('exento', 'Exento'),
            ('sujeto', 'Sujeto o ISP intracomunitario'),
            ('sujeto_agricultura', 'Sujeto Agricultura'),
            ('sujeto_isp', 'Sujeto ISP'),
            ('no_sujeto', 'No Sujeto'),
            ('no_sujeto_loc', 'No Sujeto por reglas de Localization'),
            ('no_deducible', 'No Deducible'),
            ('retencion', 'Retencion'),
            ('recargo', 'Recargo de Equivalencia'),
            ('dua', 'DUA'),
            ('ignore', 'Ignore even the base amount'),
        ],
        string="Tax Type (Spain)", default='sujeto'
    )
    l10n_es_bien_inversion = fields.Boolean('Bien de Inversion', default=False)
    l10n_es_applicability = fields.Selection(
        selection=[
            ('01', "VAT"),
            ('02', "IPSI"),
            ('03', "IGIC"),
        ],
        string="Applicability (Spain)",
    )

    l10n_es_available_regime_codes = fields.Char(
        string="Available VAT Regime Codes",
        compute="_compute_l10n_es_available_regime_codes",
        help="Technical field to enable a dynamic selection of the field \"VAT Regime Code\"",
    )
    l10n_es_regime_code = fields.Selection(
        string="VAT Regime Code",
        selection="_l10n_es_regime_code_selection",
        compute="_compute_l10n_es_regime_code",
        store=True, readonly=False,
    )

    # -------------------------------------------------------------------------
    # EDI HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_es_get_sujeto_tax_types(self):
        return ['sujeto', 'sujeto_isp', 'sujeto_agricultura']

    @api.model
    def _l10n_es_get_main_tax_types(self):
        return {'exento', 'sujeto', 'sujeto_agricultura', 'sujeto_isp', 'no_sujeto', 'no_sujeto_loc', 'no_deducible'}

    def _l10n_es_get_applicability(self):
        """Return the l10n_es_applicability of the "first" main tax in self, or False if there is
        no main tax or it isn't set on the "first" one.
        """
        main_taxes = self.filtered(lambda tax: tax.l10n_es_type in self._l10n_es_get_main_tax_types())
        return main_taxes[0].l10n_es_applicability if main_taxes else False

    # -------------------------------------------------------------------------
    # VAT REGIME CODE
    # Shared catalog for SII/TicketBAI/VeriFactu; each EDI extends `_l10n_es_regime_code_labels`
    # and/or `_l10n_es_regime_available_codes` via `super()` instead of duplicating it. A code
    # shared by more than one EDI with the same meaning belongs here; use a distinct `_xx` suffix
    # (e.g. `11_vf`) only when the meaning differs per EDI.
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_es_regime_code_labels(self):
        """Return {code: label} for the codes shared across EDI's.

        Override with `super() + dict.update(...)` to add codes specific to a given EDI.
        """
        _ = self.env._
        return {
            # Shared
            '01': _("01 - General regime operation"),
            '03': _("03 - Used goods, art, antiques and collectors' items"),
            '04': _("04 - Investment gold"),
            '05': _("05 - Travel agencies"),
            '07': _("07 - Cash basis criterion"),
            '08': _("08 - IPSI / IGIC"),
            # Same number, different meaning
            '02_sale': _("02 - Export"),
            '02_purchase': _("02 - REAGYP compensations on purchases"),
            '09_sale': _("09 - Intermediary agencies (4th Additional Provision, RD 1619/2012)"),
            '09_purchase': _("09 - Intra-Community acquisitions"),
            '12_sale': _("12 - Business premises lease not subject to withholding"),
            '12_purchase': _("12 - Business premises lease"),
            '13_sale': _("13 - Business premises lease subject and not subject to withholding"),
            '13_purchase': _("13 - Import without customs declaration (DUA)"),
            # Sales only
            '10': _("10 - Collections on behalf of third parties"),
            '11': _("11 - Lease subject to withholding"),
            '14_sale': _("14 - Pending VAT — public works certifications (public administrations)"),
            '15': _("15 - Pending VAT — continuous supply contracts"),
            '17': _("17 - OSS and IOSS"),
            '17_igic_sale': _("17 - Special regime for retail traders"),
            '18_igic_sale': _("18 - Special regime for small businesses or professionals"),
            '19_igic_sale': _("19 - Exempt domestic operations (Art. 25, Law 19/1994)"),
        }

    @api.model
    def _l10n_es_regime_code_aeat(self, code):
        """Strip the internal disambiguation suffix (e.g. '11_vf' -> '11') to get the raw AEAT value."""
        return code.split('_', 1)[0] if code else False

    @api.model
    def _l10n_es_regime_code_selection(self):
        return sorted(self._l10n_es_regime_code_labels().items(), key=lambda code_label: code_label[1])

    def _l10n_es_regime_get_available_codes(self):
        self.ensure_one()
        return self.company_id._l10n_es_regime_available_codes(
            self.type_tax_use, applicability=self.l10n_es_applicability)

    @api.depends('type_tax_use', 'l10n_es_applicability')
    def _compute_l10n_es_available_regime_codes(self):
        for tax in self:
            valid = tax._l10n_es_regime_get_available_codes()
            tax.l10n_es_available_regime_codes = ','.join(valid) if valid else False

    @api.depends('type_tax_use', 'l10n_es_applicability')
    def _compute_l10n_es_regime_code(self):
        for tax in self:
            valid = tax._l10n_es_regime_get_available_codes()
            if tax.l10n_es_regime_code not in valid:
                tax.l10n_es_regime_code = False
