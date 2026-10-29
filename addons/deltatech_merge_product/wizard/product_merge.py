# ©  2008-2021 Deltatech
# See README.rst file on addons root folder for license details


from odoo import api, fields, models


class MergeProduct(models.TransientModel):
    """
    The idea behind this wizard is to create a list of potential statement to
    merge. We use two objects, the first one is the wizard for the end-user.
    And the second will contain the object list to merge.
    """

    _inherit = "merge.object.wizard"
    _name = "merge.product.wizard"
    _description = "Merge Statement Wizard"
    _model_merge = "product.product"
    _table_merge = "product_product"

    object_ids = fields.Many2many(_model_merge, string="Statement")
    dst_object_id = fields.Many2one(_model_merge, string="Destination Statement")

    group_by_product_tmpl_id = fields.Boolean("Template")
    group_by_default_code = fields.Boolean("Reference")
    group_by_categ_id = fields.Boolean("Category")
    group_by_uom_id = fields.Boolean("Unit of measure")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids")
        if self.env.context.get("active_model") == "product.product" and active_ids:
            res["state"] = "selection"
            res["object_ids"] = [(6, 0, active_ids)]
            res["dst_object_id"] = self._get_ordered_object(active_ids)[-1].id
        if self.env.context.get("active_model") == "product.template" and active_ids:
            templates = self.env["product.template"].browse(active_ids)
            active_ids = []
            for template in templates:
                active_ids += template.product_variant_ids.ids
            res["state"] = "selection"
            res["object_ids"] = [(6, 0, active_ids)]
            res["dst_object_id"] = self._get_ordered_object(active_ids)[-1].id
        return res
