from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinMrpProduct(models.AbstractModel):
    _name = "mixin.mrp.product"
    _description = "BoM behaviour shared by product.template and product.product"

    _mrp_product_field = None
    _mrp_bom_field = None

    bom_count = fields.Integer(
        string="# Bill of Material",
        compute="_compute_bom_count",
        compute_sudo=False,
    )
    used_in_bom_count = fields.Integer(
        string="# BoM Where Used",
        compute="_compute_used_in_bom_count",
        compute_sudo=False,
    )
    mrp_product_qty = fields.Float(
        string="Manufactured",
        digits="Product Unit",
        compute="_compute_mrp_product_qty",
        compute_sudo=False,
    )
    is_kit = fields.Boolean(
        compute="_compute_is_kit",
        search="_search_is_kit",
    )

    def _get_mrp_variants(self):
        raise NotImplementedError

    def _compute_bom_count(self):
        raise NotImplementedError

    def _compute_mrp_product_qty(self):
        raise NotImplementedError

    def _compute_is_kit(self):
        raise NotImplementedError

    def _search_is_kit(self, operator, value):
        raise NotImplementedError

    def _compute_used_in_bom_count(self):
        counts = {
            record.id: count
            for record, count in self.env["mrp.bom.line"]._read_group(
                [(self._mrp_product_field, "in", self.ids)],
                [self._mrp_product_field],
                ["bom_id:count_distinct"],
            )
        }
        for record in self:
            record.used_in_bom_count = counts.get(record.id, 0)

    def action_used_in_bom(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_bom_form_action"
        )
        action["domain"] = [(f"bom_line_ids.{self._mrp_product_field}", "=", self.id)]
        return action

    def action_view_mos(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_production_action"
        )
        action["domain"] = [
            ("state", "=", "done"),
            (
                "move_finished_ids",
                "any",
                [
                    (self._mrp_product_field, "in", self.ids),
                    ("state", "!=", "cancel"),
                    ("picked", "=", True),
                ],
            ),
        ]
        action["context"] = {"search_default_filter_plan_date": 1}
        return action

    def write(self, vals):
        if "active" in vals:
            boms = self.filtered(
                lambda record: record.active != vals["active"]
            ).with_context(active_test=False)[self._mrp_bom_field]
            _debug.lifecycle(
                "boms_follow_product_active",
                records=self,
                active=vals["active"],
                boms=len(boms),
            )
            if vals["active"]:
                boms.filtered("archived_with_product").write(
                    {"active": True, "archived_with_product": False}
                )
            else:
                boms.filtered("active").write(
                    {"active": False, "archived_with_product": True}
                )
        return super().write(vals)

    def _get_still_used_bom_lines(self):
        return self.env["mrp.bom.line"].search(
            [
                ("product_id", "in", self._get_mrp_variants().ids),
                ("bom_id.active", "=", True),
            ]
        )

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [
            self.env.ref("mrp.menu_mrp_root").id
        ]
