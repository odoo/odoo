# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _get_invoice_reference_types(self):
        res = super(ResCompany, self)._get_invoice_reference_types()
        # Add BBA Structured Communication Type
        res.append(('bba', 'BBA Structured Communication'))
        return res

    invoice_reference_type = fields.Selection(string='Default Communication Type', selection='_get_invoice_reference_types',
                                              default='bba', help='You can set here the default communication that will appear on customer invoices, once validated, to help the customer to refer to that particular invoice when making the payment.')

class ResPartner(models.Model):
    """ add field to indicate default 'Communication Type' on customer invoices """
    _inherit = 'res.partner'

    @api.model
    def _get_comm_type(self):
        return self.env['res.company']._get_invoice_reference_types()

    out_inv_comm_type = fields.Selection('_get_comm_type', string='Communication Type', change_default=True,
        help='Select Default Communication Type for Outgoing Invoices.', default='none')
    out_inv_comm_algorithm = fields.Selection([
        ('random', 'Random'),
        ('date', 'Date'),
        ('partner_ref', 'Customer Reference'),
        ], string='Communication Algorithm',
        help='Select Algorithm to generate the Structured Communication on Outgoing Invoices.')

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + ['out_inv_comm_type', 'out_inv_comm_algorithm']
