from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain

from .utils import unlink_where_possible


class ProductTemplateAttributeLine(models.Model):
    _name = "product.template.attribute.line"
    _inherit = "mixin.attribute.line"
    _rec_name = "attribute_id"
    _rec_names_search = ["attribute_id", "value_ids"]
    _description = "Product Template Attribute Line"
    _requires_value = True

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        index=True,
        required=True,
        ondelete="cascade",
    )
    attribute_id = fields.Many2one(
        comodel_name="product.attribute",
        index=True,
        required=True,
        ondelete="restrict",
    )
    value_ids = fields.Many2many(
        comodel_name="product.attribute.value",
        relation="product_attribute_value_product_template_attribute_line_rel",
        string="Values",
        domain="[('attribute_id', '=', attribute_id)]",
        ondelete="restrict",
    )
    product_template_value_ids = fields.One2many(
        comodel_name="product.template.attribute.value",
        inverse_name="attribute_line_id",
        string="Product Attribute Values",
    )

    @api.onchange("attribute_id")
    def _onchange_attribute_id(self):
        if self.attribute_id.create_variant == "no_variant":
            self.value_ids = self.env["product.attribute.value"].search(
                [
                    ("attribute_id", "=", self.attribute_id.id),
                ]
            )
        else:
            self.value_ids = self.value_ids.filtered(
                lambda pav: pav.attribute_id == self.attribute_id
            )

    def _subject_label(self):
        return self.product_tmpl_id.display_name

    @api.model_create_multi
    def create(self, vals_list):
        create_values = []
        create_positions = []
        record_ids = [None] * len(vals_list)
        archived_ptal_pool = self._pool_of_reusable_archived_lines(vals_list)
        for index, value in enumerate(vals_list):
            vals = dict(value, active=value.get("active", True))
            pool_key = (vals.pop("product_tmpl_id", 0), vals.pop("attribute_id", 0))
            candidates = archived_ptal_pool.get(pool_key)
            archived_ptal = candidates.pop(0) if candidates else self.browse()
            if archived_ptal:
                archived_ptal.with_context(
                    update_product_template_attribute_values=False
                ).write(vals)
                record_ids[index] = archived_ptal.id
            else:
                create_values.append(value)
                create_positions.append(index)
        for position, record in zip(
            create_positions, super().create(create_values), strict=True
        ):
            record_ids[position] = record.id
        res = self.browse(record_ids)
        if self.env.context.get("update_product_template_attribute_values", True):
            res._update_product_template_attribute_values()
        return res

    def write(self, vals):
        values = dict(vals)
        if "product_tmpl_id" in values:
            for ptal in self:
                if ptal.product_tmpl_id.id != values["product_tmpl_id"]:
                    raise UserError(
                        _(
                            "You cannot move the attribute %(attribute)s from the product"
                            " %(product_src)s to the product %(product_dest)s.",
                            attribute=ptal.attribute_id.display_name,
                            product_src=ptal.product_tmpl_id.display_name,
                            product_dest=values["product_tmpl_id"],
                        )
                    )

        if "attribute_id" in values:
            for ptal in self:
                if ptal.attribute_id.id != values["attribute_id"]:
                    raise UserError(
                        _(
                            "On the product %(product)s you cannot transform the attribute"
                            " %(attribute_src)s into the attribute %(attribute_dest)s.",
                            product=ptal.product_tmpl_id.display_name,
                            attribute_src=ptal.attribute_id.display_name,
                            attribute_dest=values["attribute_id"],
                        )
                    )
        if not values.get("active", True):
            values["value_ids"] = [Command.clear()]
        res = super().write(values)
        if "active" in values:
            self.env.flush_all()
            self.env["product.template"].invalidate_model(["attribute_line_ids"])
        if self.env.context.get("update_product_template_attribute_values", True):
            self._update_product_template_attribute_values()
        return res

    def unlink(self):
        self.product_template_value_ids._filtered_active().unlink()
        templates = self.product_tmpl_id

        self.env.flush_all()
        still_valued = self.filtered(lambda ptal: ptal.product_template_value_ids)
        ptal_to_archive = still_valued | unlink_where_possible(
            self - still_valued, lambda ptals: ptals._unlink_without_fallback()
        )
        ptal_to_archive.action_archive()
        (templates - ptal_to_archive.product_tmpl_id)._create_variant_ids()
        return True

    def _unlink_without_fallback(self):
        return super().unlink()

    def _update_product_template_attribute_values(self):
        ProductTemplateAttributeValue = self.env["product.template.attribute.value"]
        ptav_to_create = []
        ptav_to_unlink = ProductTemplateAttributeValue
        archived_ptav_pool = self._pool_of_reusable_archived_values()
        for ptal in self:
            ptav_to_activate = ProductTemplateAttributeValue
            ptav_to_deactivate = ProductTemplateAttributeValue
            remaining_pav = set(ptal.value_ids.ids)
            for ptav in ptal.product_template_value_ids:
                if ptav.product_attribute_value_id.id not in remaining_pav:
                    if ptav.ptav_active:
                        ptav_to_unlink += ptav
                        ptav_to_deactivate += ptav
                else:
                    remaining_pav.remove(ptav.product_attribute_value_id.id)
                    if not ptav.ptav_active:
                        ptav_to_activate += ptav

            line_key = (ptal.product_tmpl_id.id, ptal.attribute_id.id)
            for pav_id in sorted(remaining_pav):
                ptav = archived_ptav_pool.pop((*line_key, pav_id), None)
                if ptav is None:
                    continue
                ptav.write({"ptav_active": True, "attribute_line_id": ptal.id})
                ptav_to_unlink -= ptav
                ptav_to_deactivate -= ptav
                remaining_pav.remove(pav_id)

            remaining_pav = (
                self.env["product.attribute.value"].sudo().browse(sorted(remaining_pav))
            )
            ptav_to_create.extend(
                {
                    "product_attribute_value_id": pav.id,
                    "attribute_line_id": ptal.id,
                    "price_extra": pav.default_extra_price,
                }
                for pav in remaining_pav
            )
            ptav_to_activate.write({"ptav_active": True})
            ptav_to_deactivate.write({"ptav_active": False})
            for ptav in ptav_to_activate:
                archived_ptav_pool.pop(self._archived_value_key(ptav), None)
            for ptav in ptav_to_deactivate:
                archived_ptav_pool.setdefault(self._archived_value_key(ptav), ptav)
        if ptav_to_unlink:
            ptav_to_unlink.unlink()
        ProductTemplateAttributeValue.create(ptav_to_create)
        if self.env.context.get("create_product_product", True):
            self.product_tmpl_id._create_variant_ids()

    @api.model
    def _pool_of_reusable_archived_lines(self, vals_list):
        wanted = {
            (vals.get("product_tmpl_id"), vals.get("attribute_id"))
            for vals in vals_list
            if vals.get("product_tmpl_id") and vals.get("attribute_id")
        }
        if not wanted:
            return {}
        domain = Domain("active", "=", False) & Domain.OR(
            Domain("product_tmpl_id", "=", template_id)
            & Domain("attribute_id", "=", attribute_id)
            for template_id, attribute_id in wanted
        )
        pool = {}
        for ptal in self.search(domain):
            pool.setdefault((ptal.product_tmpl_id.id, ptal.attribute_id.id), []).append(
                ptal
            )
        return pool

    @api.model
    def _archived_value_key(self, ptav):
        return (
            ptav.product_tmpl_id.id,
            ptav.attribute_id.id,
            ptav.product_attribute_value_id.id,
        )

    def _pool_of_reusable_archived_values(self):
        pairs = {(ptal.product_tmpl_id.id, ptal.attribute_id.id) for ptal in self}
        value_ids = self.value_ids.ids
        if not pairs or not value_ids:
            return {}
        domain = (
            Domain("ptav_active", "=", False)
            & Domain("product_attribute_value_id", "in", value_ids)
            & Domain.OR(
                Domain("product_tmpl_id", "=", template_id)
                & Domain("attribute_id", "=", attribute_id)
                for template_id, attribute_id in pairs
            )
        )
        pool = {}
        for ptav in self.env["product.template.attribute.value"].search(
            domain, order="id"
        ):
            pool.setdefault(self._archived_value_key(ptav), ptav)
        return pool

    def _without_no_variant_attributes(self):
        return self.filtered(
            lambda ptal: ptal.attribute_id.create_variant != "no_variant"
        )

    def _is_configurable(self):
        self.check_singleton()
        return (
            len(self.value_ids) >= 2
            or self.attribute_id.display_type == "multi"
            or self.value_ids.is_custom
        )

    @api.readonly
    def action_view_attribute_values(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Product Variant Values"),
            "res_model": "product.template.attribute.value",
            "view_mode": "list,form",
            "domain": [("id", "in", self.product_template_value_ids.ids)],
            "views": [
                (
                    self.env.ref(
                        "product.view_product_template_attribute_value_list"
                    ).id,
                    "list",
                ),
                (
                    self.env.ref(
                        "product.view_product_template_attribute_value_form"
                    ).id,
                    "form",
                ),
            ],
            "context": {
                "search_default_active": 1,
                "product_invisible": True,
            },
        }
