from collections import defaultdict

from odoo import fields, models


class CompraConsolidadaWizard(models.TransientModel):
    _name = 'distribuidora.compra.consolidada.wizard'
    _description = "Consolidacion de compra por fecha de pedido"

    fecha_pedido = fields.Date(
        string="Fecha de pedidos",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    def _get_consolidated_lines(self):
        self.ensure_one()
        orders = self.env['sale.order'].search([
            ('state', '=', 'sale'),
        ])
        matching_orders = orders.filtered(
            lambda o: fields.Datetime.context_timestamp(o, o.date_order).date() == self.fecha_pedido
        )
        totals = defaultdict(float)
        uom_by_product = {}
        for line in matching_orders.order_line:
            if line.display_type or not line.product_id:
                continue
            totals[line.product_id] += line.product_uom_qty
            uom_by_product[line.product_id] = line.product_uom_id.name
        return [
            {'product': product, 'qty': qty, 'uom': uom_by_product[product]}
            for product, qty in totals.items()
        ]

    def action_generar_lista(self):
        self.ensure_one()
        return self.env.ref('distribuidora_compras.action_report_compra_consolidada').report_action(self)
