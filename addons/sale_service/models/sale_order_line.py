from itertools import groupby

from odoo import api, fields, models
from odoo.db.schema import column_exists, create_column
from odoo.libs.debug_log import DebugLog
from odoo.tools import format_amount

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # used to know if generate a task and/or a project, depending on the product settings
    is_service = fields.Boolean(
        string="Is a Service",
        export_string_translation=False,
        compute="_compute_is_service",
        compute_sudo=True,
        store=True,
    )

    def _domain_sale_line_service(self, **kwargs):
        domain = [("is_service", "=", True)]
        if kwargs.get("check_is_expense", True):
            domain.append(("is_expense", "=", False))
        if kwargs.get("check_state", True):
            domain.append(("state", "=", "done"))
        return domain

    @api.depends("product_id.type")
    def _compute_is_service(self):
        self.fetch(["is_service", "product_id"])
        self.product_id.fetch(["type"])
        for so_line in self:
            so_line.is_service = so_line.product_id.type == "service"

    def _auto_init(self):
        if not column_exists(self.env.cr, "sale_order_line", "is_service"):
            _debug.lifecycle("is_service_column_backfilled", model=self._name)
            create_column(self.env.cr, "sale_order_line", "is_service", "bool")
            self.env.cr.execute("""
                UPDATE sale_order_line line
                SET is_service = (pt.type = 'service')
                FROM product_product pp
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pp.id = line.product_id
            """)
        return super()._auto_init()

    def _get_additional_name_per_id(self):
        name_per_id = (
            super()._get_additional_name_per_id()
            if not self.env.context.get("hide_partner_ref")
            else {}
        )
        if not self.env.context.get("with_price_unit"):
            return name_per_id

        sorted_sols = sorted(self, key=lambda sol: (sol.order_id.id, sol.product_id.id))
        sols_list = [
            list(sols)
            for dummy, sols in groupby(
                sorted_sols, lambda sol: (sol.order_id, sol.product_id)
            )
        ]
        for sols in sols_list:
            if len(sols) <= 1 or not all(sol.is_service for sol in sols):
                continue
            for line in sols:
                additional_name = name_per_id.get(line.id)
                name = format_amount(self.env, line.price_unit, line.currency_id)
                if additional_name:
                    name += f" {additional_name}"
                name_per_id[line.id] = f"- {name}"

        return name_per_id
