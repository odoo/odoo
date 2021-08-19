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

from odoo import models, fields, api
from odoo.tools.sql import drop_view_if_exists


class PosReportCommission(models.Model):
    _name = 'report.pos.commission'
    _auto = False
    _description = 'Commission Analysis'

    doctor_id = fields.Many2one('res.partner', string='Doctor', domain="[('is_doctor', '=', True)]")
    commission_date = fields.Date(string='Commission Date')
    amount = fields.Float(string='Amount')

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''CREATE OR REPLACE VIEW report_pos_commission AS (SELECT * FROM pos_doctor_commission)''')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
