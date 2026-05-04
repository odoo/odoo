from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pl_parent_lgu = fields.Many2one(
        string="parent LGU",
        comodel_name='res.partner',
        help="The local government unit (LGU) the partner is associated to.\n"
        "If present, it will be used in the FA (3) documents generated for this partner.\n",
    )
