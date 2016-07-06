# -*- coding: utf-'8' "-*-"

from odoo import api, models

class CodAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    @api.model
    def _get_acquirer_buttons(self, order, button_values, add_domain=None):
        cod = getattr(order.carrier_id, '%s_cod' % order.carrier_id.delivery_type, False)
        return super(CodAcquirer, self)._get_acquirer_buttons(order, button_values, add_domain=[('is_cod', '=', cod)])
