import time

from odoo import _, fields, models


class ProductMargin(models.TransientModel):
    _name = "product.margin"
    _description = "Product Margin"

    from_date = fields.Date(
        string="From",
        default=lambda self: time.strftime("%Y-01-01"),
    )
    to_date = fields.Date(
        string="To",
        default=lambda self: time.strftime("%Y-12-31"),
    )
    invoice_state = fields.Selection(
        selection=[
            ("paid", "Paid"),
            ("open_paid", "Open and Paid"),
            ("draft_open_paid", "Draft, Open and Paid"),
        ],
        default="open_paid",
        required=True,
    )

    def action_view_window(self):
        self.check_singleton()
        context = dict(self.env.context, create=False, edit=False)

        def ref(xml_id):
            proxy = self.env["ir.model.data"]
            return proxy._get_xmlid_target(xml_id)[1]

        search_view_id = ref("product.view_product_product_search")
        graph_view_id = ref("product_margin.view_product_margin_graph")
        form_view_id = ref("product_margin.view_product_margin_form")
        tree_view_id = ref("product_margin.view_product_margin_tree")

        context.update(invoice_state=self.invoice_state)

        if self.from_date:
            context.update(date_from=self.from_date)

        if self.to_date:
            context.update(date_to=self.to_date)

        views = [
            (tree_view_id, "list"),
            (form_view_id, "form"),
            (graph_view_id, "graph"),
        ]
        return {
            "name": _("Product Margins"),
            "context": context,
            "view_mode": "list,form,graph",
            "res_model": "product.product",
            "type": "ir.actions.act_window",
            "views": views,
            "view_id": False,
            "search_view_id": [search_view_id],
        }
