from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    website_id = fields.Many2one(
        comodel_name="website",
        readonly=True,
    )
    is_abandoned_cart = fields.Boolean(
        string="Abandoned Cart",
        readonly=True,
    )
    public_categ_ids = fields.Many2many(
        related="product_tmpl_id.public_categ_ids",
        string="eCommerce Categories",
    )

    def _get_fields_select(self):
        fields = super()._get_fields_select()
        fields["website_id"] = "o.website_id"
        fields["is_abandoned_cart"] = f"""
            o.date_order <= (timezone('utc', now()) - ((COALESCE(w.cart_abandoned_delay, '1.0') || ' hour')::INTERVAL))
            AND o.website_id IS NOT NULL
            AND o.state = 'draft'
            AND o.partner_id != {self.env.ref("base.public_partner").id}"""
        return fields

    def _get_from_tables(self):
        tables = super()._get_from_tables()
        tables.append(("website", "w", "LEFT JOIN", "w.id = o.website_id"))
        return tables

    def _get_fields_group_by(self):
        fields = super()._get_fields_group_by()
        fields.extend(
            [
                "o.website_id",
                "w.cart_abandoned_delay",
            ]
        )
        return fields
