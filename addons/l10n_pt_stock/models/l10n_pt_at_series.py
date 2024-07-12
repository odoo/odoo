from odoo import models, fields


class L10nPtStockATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    type = fields.Selection(selection_add=[('stock_picking', 'Stock Picking')], ondelete={'stock_picking': 'cascade'})
