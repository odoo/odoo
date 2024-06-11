# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_history_ids = fields.One2many('purchase.payment.history','purchase_id',string="Advanvce Payment Information")

    # Sale Advance Payment
    def set_purchase_advance_payment(self):
        view_id = self.env.ref('so_po_advance_payment_app.purchase_advance_payment_wizard')
        if view_id:
            pay_wiz_data={
                'name' : _('Purchase Advance Payment'),
                'type' : 'ir.actions.act_window',
                'view_type' : 'form',
                'view_mode' : 'form',
                'res_model' : 'purchase.advance.payment',
                'view_id' : view_id.id,
                'target' : 'new',
                'context' : {
                            'name':self.name,
                            'order_id':self.id,
                            'total_amount':self.amount_total,
                            'company_id':self.company_id.id,
                            'currency_id':self.currency_id.id,
                            'date_order':self.date_order,
                            'partner_id':self.partner_id.id,
                             },
            }
        return pay_wiz_data