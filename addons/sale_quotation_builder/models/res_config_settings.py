# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _set_default_sale_order_template_id_if_empty(self):
        IrDefault = self.env['ir.default']
        if not IrDefault.get('sale.order', 'sale_order_template_id'):
            template = self.env.ref('sale_quotation_builder.sale_order_template_default', raise_if_not_found=False)
            if template and template.active:
                IrDefault.set('sale.order', 'sale_order_template_id', template.id)
