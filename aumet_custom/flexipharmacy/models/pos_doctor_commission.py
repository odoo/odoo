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


class PosDoctorCommission(models.Model):
    _name = 'pos.doctor.commission'
    _description = 'Point of Sale Doctor Commission'

    doctor_id = fields.Many2one('res.partner', string='Doctor', required=True, domain="[('is_doctor', '=', True)]")
    name = fields.Char(string='Source Document', required=True)
    commission_date = fields.Date(string='Commission Date')
    amount = fields.Float(string='Amount')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('reserved', 'Invoiced'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft')
    invoice_id = fields.Many2one('account.move')
    is_invoice = fields.Boolean(string='Is Invoice', compute='_compute_invoice_state')
    commission_number = fields.Char(string='Number')
    order_id = fields.Many2one('pos.order')
    payment_id = fields.Many2one('pos.commission.payment')

    @api.depends('invoice_id')
    def _compute_invoice_state(self):
        for each in self:
            if not each.is_invoice and not each.invoice_id and each.state == 'reserved':
                each.state = 'draft';

    @api.model
    def create(self, vals):
        vals['commission_number'] = self.env['ir.sequence'].next_by_code('pos.doctor.commission.number')
        return super(PosDoctorCommission, self).create(vals)

    def cancel_state(self):
        self.state = 'cancelled'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
