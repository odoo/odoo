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
import re

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

    # returns the checksum of the ean, or -1 if the ean has not the correct length, ean must be a string
    def ean_checksum(self, ean):
        code = list(ean)
        if len(code) != 13:
            return -1

        oddsum = evensum = total = 0
        code = code[:-1] # Remove checksum
        for i in range(len(code)):
            if i % 2 == 0:
                evensum += int(code[i])
            else:
                oddsum += int(code[i])
        total = oddsum * 3 + evensum
        return int((10 - total % 10) % 10)
        
    # Returns true if the ean is a valid EAN codebar number by checking the control digit.
    # ean must be a string
    def check_ean(self, ean):
        return re.match(re.compile('\d+$'), ean) and (self.ean_checksum(ean) == int(ean[len(ean)-1]))

    # Returns a valid zero padded ean13 from an ean prefix. the ean prefix must be a string.
    def sanitize_ean(self, ean):
        ean = ean[0:13]
        ean = ean + (13-len(ean))*'0'
        return ean[0:12] + str(self.ean_checksum(ean))

    # Attempts to interpret an ean (string encoding an ean)
    # It will check its validity then return an object containing various
    # information about the ean.
    # most importantly : 
    #  - code    : the ean
    #  - type   : the type of the ean: 
    #     'price' |  'weight' | 'product' | 'cashier' | 'client' | 'discount' | 'error'
    #  - value  : if the id encodes a numerical value, it will be put there
    #  - base_code : the ean code with all the encoding parts set to zero; the one put on
    #                the product in the backend
    def parse_ean(self, ean):
        parse_result = {'encoding': 'ean13', 'type': 'error', 'code': ean, 'base_code': ean, 'value': 0}

        rules = []
        for rule in self.rule_ids:
            rules.append({'type': rule.type, 'sequence': rule.sequence, 'pattern': rule.pattern})
        
        if not self.check_ean(ean):
            return parse_result

        def is_number(char):
            n = ord(char)
            return n >= 48 and n <= 57

        def match_pattern(ean,pattern):
            for i in range(len(pattern)):
                p = pattern[i]
                e = ean[i]
                if is_number(p) and p != e:
                    return False
            return True

        def get_value(ean,pattern):
            value = 0
            decimals = 0
            for i in range(len(pattern)):
                p = pattern[i]
                v = int(ean[i])
                if p == 'N':
                    value *= 10
                    value += v
                elif p == 'D':  #FIXME precision ....
                    decimals += 1
                    value += v * pow(10,-decimals)
            return value

        def get_basecode(ean,pattern):
            base = ''
            for i in range(len(pattern)):
                p = pattern[i]
                v = ean[i]
                if p == '*' or is_number(p):
                    base += v
                else:
                    base += '0'
            return self.sanitize_ean(base)

        for rule in rules:
            if match_pattern(ean, rule['pattern']):
                parse_result['type'] = rule['type']
                parse_result['value'] = get_value(ean, rule['pattern'])
                parse_result['base_code'] = get_basecode(ean, rule['pattern'])
                return parse_result

        return parse_result

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