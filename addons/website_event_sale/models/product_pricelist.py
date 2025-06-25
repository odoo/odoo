# -*- coding: utf-8 -*-

from odoo import _, api, models

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.onchange('applied_on', 'product_id', 'product_tmpl_id', 'min_quantity')
    def _onchange_event_sale_warning(self):
        if self.min_quantity > 0:
            msg = ''
            if self.applied_on == '3_global' or self.applied_on == '2_product_category':
                msg = _("A pricelist item with a positive min. quantity will not be applied to the event tickets products.")
            elif ((self.applied_on == '1_product' and self.product_tmpl_id.service_tracking == 'event') or
                    (self.applied_on == '0_product_variant' and self.product_id.service_tracking == 'event')):
                msg = _("A pricelist item with a positive min. quantity cannot be applied to this event tickets product.")
            if msg:
                return {'warning':
                    {
                        'title': _("Warning"),
                        'message': msg
                    }
                }
