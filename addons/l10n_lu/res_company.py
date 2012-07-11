#!/usr/bin/python
# -*- coding: utf-8 -*-

from osv import fields, osv

class res_company_vat_lu(osv.osv):
    _name = 'res.company'
    _inherit = 'res.company'

    _columns = {
        'vat_matricule': fields.char('VAT Matricule', size=32, help="VAT Matricule identifing company to country vat office"),
        'vat_office': fields.char('VAT Office', size=16),
        'vat_mode': fields.selection([('sales', 'Sales'), ('receipts', 'Receipts')], 'VAT Mode', size=16),
    }

    _defaults = {
        'vat_mode': lambda *a: 'sales',
    }

res_company_vat_lu()
