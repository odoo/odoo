# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    adyen_ask_customer_for_tip = fields.Boolean('Ask Customers For Tip', help='Prompt the customer to tip.')
    module_pos_adyen = fields.Boolean(compute='_compute_module_pos_adyen', help='Technical field used to determine if pos_adyen is installed.')

    def _compute_module_pos_adyen(self):
        self.module_pos_adyen = self.env['ir.module.module'].sudo().search_count([('name', '=', 'pos_adyen'), ('state', '=', 'installed')])

    @api.constrains('adyen_ask_customer_for_tip', 'iface_tipproduct', 'tip_product_id')
    def _check_adyen_ask_customer_for_tip(self):
        for config in self:
            if config.adyen_ask_customer_for_tip and (not config.tip_product_id or not config.iface_tipproduct):
                raise ValidationError(_("Please configure a tip product for POS %s to support tipping with Adyen.") % config.name)

    @api.onchange('adyen_ask_customer_for_tip')
    def _onchange_adyen_ask_customer_for_tip(self):
        for config in self:
            if config.adyen_ask_customer_for_tip:
                config.iface_tipproduct = True
