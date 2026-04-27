# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, fields, models


class L10nChCafScale(models.Model):
    _name = 'l10n.ch.caf.scale'
    _description = 'Swiss Family Allowance Scale'
    _order = 'min_child_rank asc, min_age asc'

    fund_id = fields.Many2one('l10n.ch.compensation.fund', required=True, ondelete='cascade')

    min_age = fields.Integer(string="Min Age", default=0)
    max_age = fields.Integer(string="Max Age", default=16)

    allowance_type = fields.Selection(
        selection=[('child', 'Child Allowance'),
                   ('education', 'Education Allowance')],
        default='child',
        required=True,
        string="Type"
    )

    min_child_rank = fields.Integer(
        string="From Child",
        default=1,
        required=True,
        help="This quantity indicates from which child this amount applies."
    )

    amount = fields.Float(string="Monthly Amount", required=True)

    amount_supplementary = fields.Float(
        string="Supplementary Amount",
        help="Voluntary/Supplementary amount paid if configured on the child."
    )
