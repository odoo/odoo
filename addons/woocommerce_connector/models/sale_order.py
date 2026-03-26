import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Extend sale.order with WooCommerce traceability fields."""

    _inherit = 'sale.order'

    # ── WooCommerce Identity ──────────────────────────────────────────────────

    woo_order_id = fields.Char(
        string='WooCommerce Order ID',
        copy=False,
        index=True,
        help='WooCommerce internal order ID (numeric string).',
    )
    woo_backend_id = fields.Many2one(
        comodel_name='woocommerce.backend',
        string='WooCommerce Backend',
        copy=False,
        index=True,
        ondelete='set null',
    )
    woo_binding_id = fields.Many2one(
        comodel_name='woocommerce.order.binding',
        string='WooCommerce Binding',
        compute='_compute_woo_binding_id',
        store=False,
    )

    # ── Computes ──────────────────────────────────────────────────────────────

    @api.depends('woo_order_id', 'woo_backend_id')
    def _compute_woo_binding_id(self):
        OrderBinding = self.env['woocommerce.order.binding']
        for order in self:
            if order.woo_backend_id and order.woo_order_id:
                binding = OrderBinding.search([
                    ('backend_id', '=', order.woo_backend_id.id),
                    ('external_id', '=', order.woo_order_id),
                ], limit=1)
                order.woo_binding_id = binding
            else:
                order.woo_binding_id = False

    # ── Smart Button ─────────────────────────────────────────────────────────

    def action_view_woo_binding(self):
        self.ensure_one()
        binding = self.woo_binding_id
        if not binding:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Order',
            'res_model': 'woocommerce.order.binding',
            'view_mode': 'form',
            'res_id': binding.id,
        }
