import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """Extend product.template with WooCommerce sync visibility fields."""

    _inherit = 'product.template'

    # ── WooCommerce Binding Summary ───────────────────────────────────────────

    woo_binding_ids = fields.One2many(
        comodel_name='woocommerce.product.binding',
        inverse_name='odoo_id',
        string='WooCommerce Bindings',
        copy=False,
    )
    woo_binding_count = fields.Integer(
        string='WooCommerce Binding Count',
        compute='_compute_woo_binding_count',
    )
    woo_sync_state = fields.Selection(
        selection=[
            ('not_synced', 'Not Synced'),
            ('synced', 'Synced'),
            ('error', 'Sync Error'),
            ('pending', 'Pending'),
        ],
        string='WooCommerce Sync State',
        compute='_compute_woo_sync_state',
        store=False,
    )

    # ── Computes ──────────────────────────────────────────────────────────────

    @api.depends('woo_binding_ids')
    def _compute_woo_binding_count(self):
        for tmpl in self:
            tmpl.woo_binding_count = len(tmpl.woo_binding_ids)

    @api.depends('woo_binding_ids.sync_state')
    def _compute_woo_sync_state(self):
        for tmpl in self:
            states = tmpl.woo_binding_ids.mapped('sync_state')
            if 'error' in states:
                tmpl.woo_sync_state = 'error'
            elif 'synced' in states:
                tmpl.woo_sync_state = 'synced'
            elif 'pending' in states:
                tmpl.woo_sync_state = 'pending'
            else:
                tmpl.woo_sync_state = 'not_synced'

    # ── Smart Button ─────────────────────────────────────────────────────────

    def action_view_woo_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Bindings',
            'res_model': 'woocommerce.product.binding',
            'view_mode': 'list,form',
            'domain': [('odoo_id', '=', self.id)],
        }
