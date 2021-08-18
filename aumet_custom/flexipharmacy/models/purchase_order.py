# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api, tools, _
from datetime import datetime


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def pos_create_purchase_order(self, vals):
        order_lst = []
        for order_line_row_data in vals.get('order_line'):
            product_id = self.env['product.product'].browse(int(order_line_row_data.get('product_id')))
            qty = int(order_line_row_data.get('qty'))
            price_unit = 0.0
            product_supplierinfo_id = self.env['product.supplierinfo'].search([('name', '=', vals.get('partner_id')),
                                                                               ('product_tmpl_id', '=',
                                                                                product_id.product_tmpl_id.id)],
                                                                              limit=1, order="id desc")
            if product_supplierinfo_id:
                price_unit = product_supplierinfo_id.price
            if not product_supplierinfo_id:
                price_unit = product_id.standard_price
            order_lst.append((0, 0, {
                'date_planned': datetime.now(),
                'name': product_id.name,
                'price_unit': price_unit,
                'product_id': product_id.id,
                'product_qty': qty,
                'product_uom': product_id.uom_po_id.id or False,
            }))
        purchase_order_obj = self.env['purchase.order']
        purchase_order_obj = purchase_order_obj.create({
            'partner_id': int(vals.get('partner_id')),
            'date_order': datetime.now(),
            'company_id': self.env.company.id,
        })
        purchase_order_obj.onchange_partner_id()
        purchase_order_obj.order_line = order_lst
        purchase_order_obj.order_line._compute_tax_id()
        if vals.get('send_mail') == 'true':
            ir_model_data = self.env['ir.model.data']
            try:
                if self.env.context.get('send_rfq', False):
                    template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
                else:
                    template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase_done')[1]
            except ValueError:
                template_id = False
            try:
                ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                False
            ctx = dict(self.env.context or {})
            ctx.update({
                'default_model': 'purchase.order',
                'default_res_id': purchase_order_obj.id,
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'custom_layout': "purchase.mail_template_data_notification_email_purchase_order",
                'force_email': True
            })
            template_obj = self.env['mail.template'].browse(template_id)
            template_obj.with_context(ctx=ctx).send_mail(purchase_order_obj.id, force_send=True)
        return [purchase_order_obj.id, purchase_order_obj.name]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
