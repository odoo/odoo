# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.addons.l10n_gt.tools.partner_identifiers import GT_ADDITIONAL_IDENTIFIERS_METADATA

VAT_AFFILIATIONS = [
    ("GEN", "GEN: General VAT Regime"),
    ("EXE", "EXE: Exempt Small Taxpayer Regime"),
    ("PEQ", "PEQ: Small Taxpayer Regime"),
    ("PEE", "PEE: Special Electronic Small Taxpayer"),
    ("AGR", "AGR: Agricultural Regime"),
    ("AGE", "AGE: Agro-export Regime"),
    ("ECA", "ECA: Coffee Exporter"),
    ("EXI", "EXI: VAT Exempt (Entities or institutions legally exempt from VAT)"),
    ("PRIM", "PRIM: Primary Regime"),
    ("PECU", "PECU: Livestock Regime"),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_gt_isr_withholding_agent = fields.Boolean(
        string="ISR Retention Agent",
    )
    l10n_gt_vat_withholding_type = fields.Selection(
        selection=[
            ('special_taxpayer', "Special Taxpayer"),
            ('exporter', "Exporter"),
            ('exporter_29_89', "Exporter Decree 29-89"),
            ('public_sector', "Public Sector"),
        ],
        string="VAT Retention Type",
        help="Regime under which VAT is withheld. "
             "Leave empty if not a VAT retention agent.",
    )
    l10n_gt_vat_affiliation = fields.Selection(
        selection=VAT_AFFILIATIONS,
        string="VAT Affiliation",
        compute='_compute_l10n_gt_vat_affiliation',
        store=True,
        readonly=False,
        init_storage='_init_column_l10n_gt_vat_affiliation',
        help="""Selects the VAT affiliation of the taxpayer:
        GEN - General VAT Regime - Applicable to taxpayers with commercial, industrial or service activities. They must declare and pay VAT monthly, using the tax debit and credit method.
        EXE - VAT Exempt - Applies to government entities, non-profit associations and exempt activities according to the law. They do not generate or pay VAT, but must meet specific requirements before the SAT.
        PEQ - Small Taxpayer - For individuals or legal entities with annual income up to a limit established by the SAT. They pay a fixed percentage of their gross sales and file quarterly returns.
        PEE - Small Electronic Taxpayer - Similar to the Small Taxpayer regime, but adapted for electronic operations, allowing digital declarations and billing.
        AGR - Agricultural Regime - Designed for agricultural activities with specific tax benefits, allowing credits and declarations adapted to agroindustrial production.
        AGE - Electronic Agricultural Regime - Same as the agricultural regime, but for taxpayers who operate electronically, facilitating tax declaration and control processes.
        ECA - Exporter of Goods and Services - Explanation: For companies that export. It allows you to request tax credit refunds for exports and enjoy certain tax benefits.
        EXI - Exempt for Specific Income - Explanation: Applies to sectors or activities exempt from taxes according to special legislation, such as diplomatic services and certain exports of specific goods or services.
        PRIM - Primary Regime.
        PECU - Livestock Regime.
        """,
    )

    def _init_column_l10n_gt_vat_affiliation(self):
        # Only company partners and their contacts get a default, so skip computing it on every partner.
        self.env.cr.execute("""
            UPDATE res_partner partner
               SET l10n_gt_vat_affiliation = 'GEN'
              FROM res_company company, res_country country
             WHERE company.partner_id = partner.commercial_partner_id
               AND country.id = company.account_fiscal_country_id
               AND country.code = 'GT'
        """)

    @api.depends('country_code')
    def _compute_l10n_gt_vat_affiliation(self):
        company_partners = self.env['res.company'].sudo().search([('partner_id', 'in', self.ids)]).partner_id
        for partner in self:
            affiliation = partner.l10n_gt_vat_affiliation
            if partner in company_partners:
                affiliation = (affiliation or 'GEN') if partner.country_code == 'GT' else False
            partner.l10n_gt_vat_affiliation = affiliation

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            'l10n_gt_isr_withholding_agent',
            'l10n_gt_vat_withholding_type',
            'l10n_gt_vat_affiliation',
        ]

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **GT_ADDITIONAL_IDENTIFIERS_METADATA}

    @api.model
    def _get_portal_additional_identifiers(self, country_sudo, **kwargs):
        optional, mandatory = super()._get_portal_additional_identifiers(country_sudo, **kwargs)
        if self.env.company.account_fiscal_country_id.code == 'GT' and country_sudo.code == 'GT':
            optional.add('GT_CUI')
        return optional, mandatory
