# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

import openerp
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class barcode_nomenclature(osv.osv):
    _name = 'barcode.nomenclature'
    _columns = {
        'name':             fields.char('Nomenclature Name', size=32, required=True, help='An internal identification of the barcode nomenclature'),
        #'convert_to_ean13': fields.boolean('Convert to EAN-13',help='Numerical Barcodes shorter than EAN-13 will be automatically converted to EAN-13'),
        'rule_ids':        fields.one2many('barcode.rule','barcode_nomenclature_id','Rules', help='The list of barcode rules'),
    }

class barcode_rule(osv.osv):
    _name = 'barcode.rule'
    _order = 'sequence asc'
    _columns = {
        'name':     fields.char('Rule Name', size=32, required=True, help='An internal identification for this barcode nomenclature rule'),
        'barcode_nomenclature_id':     fields.many2one('barcode.nomenclature','Barcode Nomenclature'),
        'sequence': fields.integer('Sequence', help='Used to order rules such that rules with a smaller sequence match first'),
        #'encoding': fields.selection([('any','Any'),('ean13','EAN-13'),('ean8','EAN-8'),('codabar','Codabar'),('upca','UPC-A'),('upce','UPC-E')],'Encoding',help='This rule will apply only if the barcode is encoded with the specified encoding'),
        'type':     fields.selection([('product','Unit Product'),('weight','Weighted Product'),('price','Priced Product'),('discount','Discounted Product'),('client','Client'),('cashier','Cashier')],'Type', required=True),
        'pattern':  fields.char('Barcode Pattern', size=32, help="The barcode matching pattern"),
        #'alias':    fields.char('Alias',size=32,help='The matched pattern will alias to this barcode'),      
    }

    _defaults = {
        'type': 'product',
        'pattern': '*',
        #'encoding': 'any',
    }