# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # -- Colombian Tax Classification --
    l10n_co_edi_tax_regime = fields.Selection(
        selection=[
            ('common', 'Regimen Comun (Responsable de IVA)'),
            ('simple', 'Regimen Simple de Tributacion (SIMPLE)'),
            ('not_responsible', 'No Responsable de IVA'),
        ],
        string='Tax Regime',
        help='Colombian tax regime classification. Used for fiscal position '
             'auto-detection and electronic invoicing.',
    )
    l10n_co_edi_gran_contribuyente = fields.Boolean(
        string='Gran Contribuyente',
        help='Check if the partner is classified as Gran Contribuyente by DIAN. '
             'Gran Contribuyentes have special withholding obligations.',
    )
    l10n_co_edi_autorretenedor = fields.Boolean(
        string='Autorretenedor',
        help='Check if the partner is designated as a self-withholding agent by DIAN.',
    )
    l10n_co_edi_fiscal_responsibility_ids = fields.Many2many(
        'l10n_co_edi.fiscal.responsibility',
        'l10n_co_edi_partner_fiscal_resp_rel',
        'partner_id', 'responsibility_id',
        string='Fiscal Responsibilities',
        help='DIAN fiscal responsibility codes applicable to this partner.',
    )
    l10n_co_edi_fiscal_responsibilities = fields.Char(
        string='Fiscal Responsibility Codes',
        compute='_compute_l10n_co_edi_fiscal_responsibilities',
        store=True,
        help='Comma-separated DIAN fiscal responsibility codes for XML generation.',
    )
    l10n_co_edi_ciiu_code = fields.Char(
        string='CIIU Code',
        help='Primary CIIU (ISIC) economic activity code.',
    )

    @api.depends('l10n_co_edi_fiscal_responsibility_ids')
    def _compute_l10n_co_edi_fiscal_responsibilities(self):
        for partner in self:
            codes = partner.l10n_co_edi_fiscal_responsibility_ids.mapped('code')
            partner.l10n_co_edi_fiscal_responsibilities = ','.join(codes) if codes else ''
