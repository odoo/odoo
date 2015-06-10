# coding: utf-8

from openerp import models, api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _get_partner_to_invoice(self, picking):
        if 'partner_to_invoice_id' in self.env.context:
            return self.env.context['partner_to_invoice_id']
        else:
            return super(StockPicking, self)._get_partner_to_invoice(picking)
