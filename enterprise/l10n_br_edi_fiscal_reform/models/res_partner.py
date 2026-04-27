# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_br_tax_regime = fields.Selection(selection_add=[
        ('simplifiedHybrid', 'simplifiedHybrid'),
        ('simplifiedOverGrossthreshold',),
    ])  # TODO JOV: we used the Avalara technical names in l10n_br_avatax, fix in master
    l10n_br_is_cbs_ibs_taxpayer = fields.Boolean(
        'CBS/IBS Taxpayer',
        default=True,
        help='Brazil: Indicates that this entity is subject to CBS/IBS taxation. Used for exempt operations or special regimes.'
    )
    l10n_br_is_cbs_ibs_normal = fields.Boolean(
        'CBS/IBS Normal',
        default=True,
        help='Brazil: Indicates whether the contact or company under the simplified regime is classified as Normal or Mixed taxation. When enabled, it means the entity follows the Normal regime; when disabled, it indicates the Mixed regime.'
    )
    l10n_br_cbs_credit = fields.Float(
        'CBS Presumed Credit (%)',
        help='Brazil: Percentage of presumed CBS credit for entities under Simples Nacional "misto" regime.'
    )
    l10n_br_ibs_credit = fields.Float(
        'IBS Presumed Credit (%)',
        help='Brazil: Percentage of presumed IBS credit for entities under Simples Nacional "misto" regime.'
    )
    l10n_br_is_cashback_applied = fields.Boolean(
        'Apply Cashback',
        help='Brazil: Enables CBS/IBS cashback calculation for eligible consumers in outbound operations.'
    )
    l10n_br_entity_type = fields.Selection(
        [
            ('individual', 'Individual'),
            ('business', 'Business'),
            ('foreign', 'Foreign'),
            ('federalGovernment', 'Federal Government'),
            ('stateGovernment', 'State Government'),
            ('cityGovernment', 'City Government'),
            ('mixedCapital', 'Mixed Capital'),
            ('coops', 'Coops'),
        ],
        compute='_compute_l10n_br_entity_type',
        store=True,
        readonly=False,
        string='Entity Type',
        help='Brazil: Defines the type of entity.'
    )

    @api.depends('is_company')
    def _compute_l10n_br_entity_type(self):
        for partner in self:
            partner.l10n_br_entity_type = 'business' if partner.is_company else 'individual'
