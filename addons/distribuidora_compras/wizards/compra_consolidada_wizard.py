from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models

DELIVERY_WEEKDAYS = {0, 2, 4}  # lunes, miercoles, viernes (Python: lunes=0)


class CompraConsolidadaWizard(models.TransientModel):
    _name = 'distribuidora.compra.consolidada.wizard'
    _description = "Consolidacion de compra por fecha de entrega"

    fecha_entrega = fields.Date(
        string="Fecha de entrega",
        required=True,
        default=lambda self: self._default_fecha_entrega(),
    )

    @api.model
    def _default_fecha_entrega(self):
        today = fields.Date.context_today(self)
        offset = 0
        while (today + timedelta(days=offset)).weekday() not in DELIVERY_WEEKDAYS:
            offset += 1
        return today + timedelta(days=offset)

    def _get_consolidated_lines(self):
        self.ensure_one()
        orders = self.env['sale.order'].search([
            ('state', '=', 'sale'),
            ('commitment_date', '!=', False),
        ])
        matching_orders = orders.filtered(
            lambda o: fields.Datetime.context_timestamp(o, o.commitment_date).date() == self.fecha_entrega
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
