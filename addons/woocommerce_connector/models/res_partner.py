import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Extend res.partner with WooCommerce customer binding visibility."""

    _inherit = 'res.partner'

    woo_customer_binding_ids = fields.One2many(
        comodel_name='woocommerce.customer.binding',
        inverse_name='odoo_id',
        string='WooCommerce Bindings',
        copy=False,
    )
    woo_customer_binding_count = fields.Integer(
        string='WooCommerce Bindings',
        compute='_compute_woo_customer_binding_count',
    )

    @api.depends('woo_customer_binding_ids')
    def _compute_woo_customer_binding_count(self):
        for partner in self:
            partner.woo_customer_binding_count = len(partner.woo_customer_binding_ids)

    def action_view_woo_customer_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Customer Bindings',
            'res_model': 'woocommerce.customer.binding',
            'view_mode': 'list,form',
            'domain': [('odoo_id', '=', self.id)],
        }
