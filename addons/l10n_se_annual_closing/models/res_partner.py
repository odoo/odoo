# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_se_sni_ids = fields.One2many(comodel_name='l10n_se.partner.sni', inverse_name='partner_id', string='SNI Codes')
    l10n_se_primary_sni_id = fields.Many2one(comodel_name='l10n_se.sni', string='Primary SNI Code', compute='_compute_primary_sni', store=True, help='The SNI code with the lowest sequence number on the company.')

    @api.depends(
        'commercial_partner_id.l10n_se_sni_ids',
        'commercial_partner_id.l10n_se_sni_ids.sequence',
        'commercial_partner_id.l10n_se_sni_ids.sni_id',
    )
    def _compute_primary_sni(self):
        """Primary SNI code of the company: the assignment with the lowest sequence.

        SNI codes are kept on the commercial partner (the company); its contacts
        get the same primary code.
        """
        for partner in self:
            first = partner.commercial_partner_id.l10n_se_sni_ids[:1]
            partner.l10n_se_primary_sni_id = first.sni_id if first else False
