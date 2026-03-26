import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """WooCommerce settings panel in Odoo General Settings."""

    _inherit = 'res.config.settings'

    # These are convenience links to the backend form — not stored params.
    # Actual configuration lives on woocommerce.backend records.

    module_woocommerce_connector = fields.Boolean(
        string='WooCommerce Integration',
        help='Enable the WooCommerce channel integration.',
    )

    woo_backend_count = fields.Integer(
        string='WooCommerce Backends',
        compute='_compute_woo_backend_count',
    )

    @api.depends()
    def _compute_woo_backend_count(self):
        count = self.env['woocommerce.backend'].search_count([])
        for rec in self:
            rec.woo_backend_count = count

    def action_open_woo_backends(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Backends',
            'res_model': 'woocommerce.backend',
            'view_mode': 'list,form',
        }
