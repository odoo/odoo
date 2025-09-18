from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("type")
    def _compute_expense_policy(self):
        super()._compute_expense_policy()
        self.filtered(lambda t: t.is_storable).expense_policy = "no"

    @api.depends("type")
    def _compute_service_type(self):
        super()._compute_service_type()
        self.filtered(lambda t: t.is_storable).service_type = "manual"
