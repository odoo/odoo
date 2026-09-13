from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_product_pricelist = fields.Many2one(
        comodel_name="product.pricelist",
        string="Pricelist",
        compute="_compute_property_product_pricelist",
        inverse="_inverse_property_product_pricelist",
        company_dependent=False,
        domain=lambda self: [("company_id", "in", (self.env.company.id, False))],
        help="Used for sales to the current partner",
    )

    specific_property_product_pricelist = fields.Many2one(
        comodel_name="product.pricelist",
        company_dependent=True,
    )

    is_manufacturer = fields.Boolean(string="Manufacturer")
    manufactured_product_ids = fields.One2many(
        comodel_name="product.template",
        inverse_name="manufacturer_id",
        string="Manufactured Products",
    )
    count_manufactured_products = fields.Count(
        count_of="manufactured_product_ids",
        string="Product Count",
        readonly=True,
    )

    @api.depends_context("company", "country_code")
    @api.depends("country_id", "specific_property_product_pricelist")
    def _compute_property_product_pricelist(self):
        res = self.env["product.pricelist"]._get_partner_pricelist_multi(self._ids)
        for partner in self:
            partner.property_product_pricelist = res.get(partner.id)

    def _inverse_property_product_pricelist(self):
        defaults = self.env["product.pricelist"]._get_country_pricelist_multi(
            self.country_id.ids
        )
        for partner in self:
            default_for_country = defaults.get(partner.country_id.id)
            actual = partner.specific_property_product_pricelist
            if partner.property_product_pricelist or (
                actual and default_for_country and default_for_country.id != actual.id
            ):
                partner.specific_property_product_pricelist = (
                    False
                    if partner.property_product_pricelist.id == default_for_country.id
                    else partner.property_product_pricelist.id
                )

    def _synced_commercial_fields(self):
        return [
            *super()._synced_commercial_fields(),
            "specific_property_product_pricelist",
        ]

    def action_view_manufacturer_products(self):
        self.check_singleton()
        return {
            "name": self.env._("Products"),
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "list,form",
            "context": {
                "search_default_manufacturer_id": self.id,
                "default_manufacturer_id": self.id,
            },
        }
