from collections import defaultdict

from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    wip_production_ids = fields.Many2many(
        comodel_name="mrp.production",
        relation="wip_move_production_rel",
        column1="move_id",
        column2="production_id",
        string="Relevant WIP MOs",
        copy=False,
        help="The MOs that this WIP entry was based on. Expected to be set at time of WIP entry creation.",
    )
    wip_production_count = fields.Count(
        count_of="wip_production_ids",
        string="Manufacturing Orders Count",
    )

    def copy(self, default=None):
        records = super().copy(default)
        for record, source in zip(records.sudo(), self.sudo(), strict=True):
            record.wip_production_ids = source.wip_production_ids
        return records

    def action_view_wip_production(self):
        self.check_singleton()
        action = {
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
        }
        if len(self.wip_production_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": self.wip_production_ids.id,
                }
            )
        else:
            action.update(
                {
                    "name": _("WIP MOs of %s", self.name),
                    "domain": [("id", "in", self.wip_production_ids.ids)],
                    "view_mode": "list,form",
                }
            )
        return action


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_invoiced_qty_per_product(self):
        qties = defaultdict(float)
        res = super()._get_invoiced_qty_per_product()
        invoiced_products = self.env["product.product"].concat(*res.keys())
        bom_kits = self.env["mrp.bom"]._get_bom_by_product(
            invoiced_products, company_id=self.company_id[:1].id, bom_type="phantom"
        )
        for product, qty in res.items():
            bom_kit = bom_kits[product]
            if bom_kit:
                invoiced_qty = product.uom_id._get_quantity_in_unit(
                    qty, bom_kit.product_uom_id, round=False
                )
                factor = invoiced_qty / bom_kit.product_qty
                _dummy, bom_sub_lines = bom_kit._explode(product, factor)
                for bom_line, bom_line_data in bom_sub_lines:
                    qties[bom_line.product_id] += (
                        bom_line.product_uom_id._get_quantity_in_unit(
                            bom_line_data["qty"], bom_line.product_id.uom_id
                        )
                    )
            else:
                qties[product] += qty
        return qties
