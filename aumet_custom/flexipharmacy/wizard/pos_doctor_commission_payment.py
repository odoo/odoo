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

from odoo.exceptions import Warning
from odoo import models, fields, api, _


class POSDoctorCommissionPayment(models.TransientModel):
    _name = 'pos.doctor.commission.payment'
    _description = "Point of Sale Commission Payment Report"

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    doctor_ids = fields.Many2many('res.partner', string='Doctor', domain="[('is_doctor', '=', True)]")

    @api.constrains('start_date', 'end_date')
    def _check_date(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise Warning(_('End Date should be greater than Start Date.'))

    def print_report(self):
        data_filter = []
        if self.start_date:
            data_filter = [('commission_date', '>=', self.start_date)]
        if self.end_date:
            data_filter.append(('commission_date', '<=', self.end_date))
        if self.doctor_ids:
            data_filter.append(('doctor_id', 'in', self.doctor_ids.ids))
        commission_browse = self.env['pos.doctor.commission'].search(data_filter)
        data = {}
        data_new = {}
        if not commission_browse:
            raise Warning(_("There is no any record's are available..!!"))
        for record in commission_browse:
            if record.doctor_id.id not in data:
                data[record.doctor_id.id] = [{'name': record.doctor_id.name,
                                             'source_document': record.name,
                                             'date': record.commission_date,
                                             'amount': record.amount,
                                             'state': record.state}]
            else:
                data[record.doctor_id.id].append({'name': record.doctor_id.name,
                                                 'source_document': record.name,
                                                 'date': record.commission_date,
                                                 'amount': record.amount,
                                                 'state': record.state})
        data_new.update({'commission': data})
        return self.env.ref('flexipharmacy.pos_doctor_payment_report').report_action(self, data=data_new)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: