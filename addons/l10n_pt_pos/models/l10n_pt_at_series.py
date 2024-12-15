from odoo import fields, models


class L10nPtPosATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    type = fields.Selection(selection_add=[('pos_order', 'POS Order')], ondelete={'pos_order': 'cascade'})
