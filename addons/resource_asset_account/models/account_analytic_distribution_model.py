from odoo import fields, models


class AccountAnalyticDistributionModel(models.Model):
    _inherit = "account.analytic.distribution.model"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        ondelete="cascade",
        help="Asset for which this analytic distribution will be automatically applied. "
        "When this asset is selected on an invoice line or sales order, the defined "
        "analytic distribution will be used automatically",
    )
