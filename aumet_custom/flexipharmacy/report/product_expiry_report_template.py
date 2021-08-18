# -*- coding: utf-8 -*-
#################################################################################
# Author : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, api


class GroupByCustomerPaymentPdf(models.AbstractModel):
    _name = 'report.flexipharmacy.product_exp_report_template'
    _description = 'Product Expiry Report Template'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'data': data['stock'],
            'doc_model': 'product.expiry.report',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
