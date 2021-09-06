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
from odoo import models, fields, tools, api, _


class CustomerSaleReturnReportTemplate(models.AbstractModel):
    _name = 'report.flexipharmacy.customer_sale_return_template'
    _description = "aspl pos report customer sale return temp"

    @api.model
    def _get_report_values(self, docids, data=None):
        partner_id = self.env['res.partner'].search([('id', 'in', data["customer_ids"])])
        docids = self.env['pos.order'].search([('id', 'in', data['order_ids'])])
        return {
            'doc_ids': docids,
            'doc_model': 'pos.order',
            'docs': partner_id,
            'data': data,
            'get_record_id': self.get_record_id,
            'get_return_record_id': self.get_return_record_id,
        }

    def get_record_id(self, partner, order):
        order_ids = self.env['pos.order'].search(
            [('id', 'in', order.ids), ('partner_id', '=', partner.id), ('amount_total', '>=', 0)])
        return order_ids

    def get_return_record_id(self, partner, order):
        order_ids = self.env['pos.order'].search(
            [('id', 'in', order.ids), ('partner_id', '=', partner.id), ('amount_total', '<', 0)])
        return order_ids

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
