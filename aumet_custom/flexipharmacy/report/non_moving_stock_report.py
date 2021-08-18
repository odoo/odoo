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
from odoo import fields, models, api


class NonMovingStockReport(models.AbstractModel):
    _name = 'report.flexipharmacy.non_moving_stock_template'
    _description = "Non Moving Stock Template"

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'data': data['products'],
            'doc_model': 'non.moving.stock',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
