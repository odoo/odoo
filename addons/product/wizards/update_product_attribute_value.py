from odoo import api, fields, models
from odoo.fields import Command


class UpdateProductAttributeValue(models.TransientModel):
    _name = "update.product.attribute.value"
    _description = "Update product attribute value"

    attribute_value_id = fields.Many2one(
        comodel_name="product.attribute.value",
        required=True,
    )
    mode = fields.Selection(
        selection=[
            ("add", "Add to existing products"),
            ("update_extra_price", "Update the extra price on existing products"),
        ],
        required=True,
    )
    message = fields.Char(compute="_compute_message")
    product_count = fields.Integer(compute="_compute_product_counts")
    customized_product_count = fields.Integer(compute="_compute_product_counts")

    @api.depends(
        "product_count", "customized_product_count", "mode", "attribute_value_id"
    )
    def _compute_message(self):
        self.message = ""
        for wizard in self:
            if wizard.mode == "add":
                wizard.message = self.env._(
                    'You are about to add the value "%(attribute_value)s" to %(product_count)s products.',
                    attribute_value=wizard.attribute_value_id.name,
                    product_count=wizard.product_count,
                )
            elif wizard.mode == "update_extra_price":
                if wizard.customized_product_count:
                    wizard.message = self.env._(
                        "You are about to update the extra price of %(product_count)s"
                        " products, including %(customized_count)s with a price"
                        " already customized away from the previous default. Their"
                        " custom price will be overwritten.",
                        product_count=wizard.product_count,
                        customized_count=wizard.customized_product_count,
                    )
                else:
                    wizard.message = self.env._(
                        "You are about to update the extra price of %s products.",
                        wizard.product_count,
                    )

    def _get_product_count_key(self):
        self.check_singleton()
        if self.mode == "add":
            return ("add", self.attribute_value_id.attribute_id.id)
        if self.mode == "update_extra_price":
            return ("update_extra_price", self.attribute_value_id.id)
        return None

    @api.model
    def _get_domain_product_count(self, key):
        mode, record_id = key
        if mode == "add":
            return [("attribute_line_ids.attribute_id", "=", record_id)]
        return [("attribute_line_ids.value_ids", "=", record_id)]

    @api.depends("mode", "attribute_value_id")
    def _compute_product_counts(self):
        self.product_count = 0
        self.customized_product_count = 0
        ProductTemplate = self.env["product.template"]
        keys_by_wizard = {wizard: wizard._get_product_count_key() for wizard in self}
        counts = {
            key: ProductTemplate.search_count(self._get_domain_product_count(key))
            for key in set(keys_by_wizard.values()) - {None}
        }
        customized = self._get_customized_counts_per_value()
        for wizard in self:
            wizard.product_count = counts.get(keys_by_wizard[wizard], 0)
            wizard.customized_product_count = customized.get(
                wizard.attribute_value_id.id, 0
            )

    def _get_customized_counts_per_value(self):
        """How many templates price each attribute value away from its default.

        One `_read_group` for the whole recordset rather than a `search_count`
        per wizard: the count cannot be expressed as a domain, because the
        threshold it compares against -- the value's own `default_extra_price`
        -- differs per row, and a domain cannot compare two fields. Grouping by
        (value, price) instead returns one row per distinct price actually in
        use, which is a handful, and the comparison happens over those.

        :return: {product.attribute.value id: count of templates priced away}
        :rtype: dict
        """
        wizards = self.filtered(
            lambda wizard: (
                wizard.mode == "update_extra_price" and wizard.attribute_value_id
            )
        )
        values = wizards.attribute_value_id
        if not values:
            return {}
        default_per_value = {value.id: value.default_extra_price for value in values}
        counts = {}
        groups = self.env["product.template.attribute.value"]._read_group(
            [
                ("product_attribute_value_id", "in", values.ids),
                ("product_tmpl_id.company_id", "in", self.env.companies.ids + [False]),
            ],
            groupby=["product_attribute_value_id", "price_extra"],
            aggregates=["__count"],
        )
        for value, price_extra, count in groups:
            if price_extra != default_per_value[value.id]:
                counts[value.id] = counts.get(value.id, 0) + count
        return counts

    def action_confirm(self):
        self.check_singleton()
        if self.mode == "add":
            self._add_value_to_existing_attribute_lines()
        elif self.mode == "update_extra_price":
            self._update_extra_price_on_existing_products()

    def _add_value_to_existing_attribute_lines(self):
        ptals = self.env["product.template.attribute.line"].search(
            [
                ("attribute_id", "=", self.attribute_value_id.attribute_id.id),
                ("product_tmpl_id.company_id", "in", self.env.companies.ids + [False]),
            ]
        )
        ptals.write({"value_ids": [Command.link(self.attribute_value_id.id)]})

    def _update_extra_price_on_existing_products(self):
        ptavs = self.env["product.template.attribute.value"].search(
            [
                ("product_attribute_value_id", "=", self.attribute_value_id.id),
                ("product_tmpl_id.company_id", "in", self.env.companies.ids + [False]),
            ]
        )
        ptavs.write({"price_extra": self.attribute_value_id.default_extra_price})
