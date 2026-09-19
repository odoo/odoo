from odoo import api, fields, models


class LoyaltyHistory(models.Model):
    _name = "loyalty.history"
    _description = "History for Loyalty cards and Ewallets"
    _order = "id desc"

    card_id = fields.Many2one(
        comodel_name="loyalty.card",
        index=True,
        required=True,
        ondelete="cascade",
    )
    # Stored: `loyalty_history_company_rule` filters on it, and a non-stored related
    # turns every evaluation of that rule into a LEFT JOIN on loyalty_card.
    company_id = fields.Many2one(
        related="card_id.company_id",
    )

    description = fields.Text(required=True)

    issued = fields.Float()
    used = fields.Float()

    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(
        model_field="order_model",
        readonly=True,
    )
    order_description = fields.Char(
        string="Order",
        compute="_compute_order_description",
    )
    order_portal_url = fields.Char(compute="_compute_order_portal_url")

    @api.depends("order_model", "order_id")
    def _compute_order_description(self):
        """Name each line's order, one query per model for the whole set.

        A field and not a method because the portal renders a page of lines and
        asked each one on its own -- one query per line. Grouping by `order_model`
        also gives the three answers the method did not have: `order_id` is a
        `Many2oneReference`, so there is no foreign key keeping it in step, and a
        line can name no order at all (`self.env[False]`), a model whose module has
        since been uninstalled, or an order that has since been deleted.
        """
        self.order_description = False
        for model, lines in self.grouped("order_model").items():
            if not model or model not in self.env:
                continue
            orders = self.env[model].browse(lines.mapped("order_id")).exists()
            names = dict(zip(orders.ids, orders.mapped("display_name"), strict=True))
            for line in lines:
                line.order_description = names.get(line.order_id, False)

    @api.depends("order_model", "order_id")
    def _compute_order_portal_url(self):
        """The customer-facing link to each line's order, if its model has one."""
        self.order_portal_url = False
