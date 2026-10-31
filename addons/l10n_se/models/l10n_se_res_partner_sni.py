# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class L10nSePartnerSni(models.Model):
    """SNI code assignments for partners — supports multiple codes per partner."""

    _name = 'l10n_se.partner.sni'
    _description = 'Partner SNI Code Assignment'
    _order = 'sequence, id'

    _unique_partner_sni = models.Constraint(
        'unique(partner_id, sni_id)',
        'This SNI code is already assigned to this partner.',
    )

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sni_id = fields.Many2one(
        'l10n_se.sni',
        string='SNI Code',
        required=True,
        ondelete='restrict',
        index=True,
    )
    sequence = fields.Integer(
        default=10,
        help='Lower sequence means higher priority. The first SNI code is considered primary.',
    )
    sni_code = fields.Char(related='sni_id.code', string='Code')
    sni_name = fields.Char(related='sni_id.name', string='Industry')
