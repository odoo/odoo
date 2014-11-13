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
from openerp import tools, models, fields, api
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class barcode_nomenclature(osv.osv):
    _name = 'barcode.nomenclature'
    _columns = {
        'name':             fields.char('Nomenclature Name', size=32, required=True, help='An internal identification of the barcode nomenclature'),
        'rule_ids':        fields.one2many('barcode.rule','barcode_nomenclature_id','Rules', help='The list of barcode rules'),
    }

    # returns the checksum of the ean13, or -1 if the ean has not the correct length, ean must be a string
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
        
    # Returns a valid zero padded ean13 from an ean prefix. the ean prefix must be a string.
    def sanitize_ean(self, ean):
        ean = ean[0:13]
        ean = ean + (13-len(ean))*'0'
        return ean[0:12] + str(self.ean_checksum(ean))

    # Attempts to interpret an barcode (string encoding a barcode)
    # It will return an object containing various information about the barcode.
    # most importantly : 
    #  - code    : the barcode
    #  - type   : the type of the barcode: 
    #      'price' |  'weight' | 'product' | 'cashier' | 'client' | 'discount' | 'lot' | 
    #            'package' | 'location' | 'error'
    #  - value  : if the id encodes a numerical value, it will be put there
    #  - base_code : the barcode code with all the encoding parts set to zero; the one put on
    #                the product in the backend
    def parse_barcode(self, barcode):
        parsed_result = {
            'encoding': '', 
            'type': 'error', 
            'code': barcode, 
            'base_code': barcode, 
            'value': 0}
        
        def match_pattern(barcode,pattern):
            if(len(barcode) < len(pattern.replace('{','').replace('}',''))):
                return False # match of this pattern is impossible
            numerical_content  = False
            j=0
            for i in range(len(pattern)):
                p = pattern[i]
                if p == '{' or p == '}':
                    numerical_content = not numerical_content
                    continue

                if not numerical_content and p != '*' and p != barcode[j]:
                    return False
                j+=1
            return True

        def get_value(barcode,pattern):
            value = 0
            decimals = 0
            numerical_content = False
            j = 0
            for i in range(len(pattern)):
                p = pattern[i]
                if not numerical_content and p != "{":
                    j+=1
                    continue
                elif p == "{":
                    numerical_content = True
                    continue
                elif p == "}":
                    break;

                v = int(barcode[j])
                if p == 'N':
                    value *= 10
                    value += v
                elif p == 'D':  #FIXME precision ....
                    decimals += 1
                    value += v * pow(10,-decimals)
                j+=1
            return value

        def get_basecode(barcode,pattern,encoding):
            base = ''
            numerical_content = False
            j = 0
            for i in range(len(pattern)):
                p = pattern[i]
                if p == '{' or p == '}':
                    numerical_content = not numerical_content
                    continue

                if numerical_content:
                    base += '0'
                else:
                    base += barcode[j]
                j+=1

            for i in range(j, len(barcode)): # Read the rest of the barcode
                base += barcode[i]
            if encoding == "ean13":
                base = self.sanitize_ean(base)
            return base

        rules = []
        for rule in self.rule_ids:
            rules.append({'type': rule.type, 'encoding': rule.encoding, 'sequence': rule.sequence, 'pattern': rule.pattern, 'alias': rule.alias})

        for rule in rules:
            if match_pattern(barcode, rule['pattern']):
                if rule['type'] == 'alias':
                    barcode = rule['alias']
                    parsed_result['code'] = barcode
                else:
                    parsed_result['encoding'] = rule['encoding']
                    parsed_result['type'] = rule['type']
                    parsed_result['value'] = get_value(barcode, rule['pattern'])
                    parsed_result['base_code'] = get_basecode(barcode, rule['pattern'], parsed_result['encoding'])
                    return parsed_result
        return parsed_result

class barcode_rule(models.Model):
    _name = 'barcode.rule'
    _order = 'sequence asc'
        
    _columns = {
        'name':     fields.char('Rule Name', size=32, required=True, help='An internal identification for this barcode nomenclature rule'),
        'barcode_nomenclature_id':     fields.many2one('barcode.nomenclature','Barcode Nomenclature'),
        'sequence': fields.integer('Sequence', help='Used to order rules such that rules with a smaller sequence match first'),
        'encoding': fields.selection([('any','Any'),('ean13','EAN-13')],'Encoding',required=True,help='This rule will apply only if the barcode is encoded with the specified encoding'),
        'type':     fields.selection([('alias','Alias'),('product','Unit Product')],'Type', required=True),
        'pattern':  fields.char('Barcode Pattern', size=32, help="The barcode matching pattern"),
        'alias':    fields.char('Alias',size=32,help='The matched pattern will alias to this barcode',required=True),      
    }

    _defaults = {
        'type': 'product',
        'pattern': '*',
        'encoding': 'any',
        'alias': "0",
    }

    @api.one
    @api.constrains('pattern')
    def _check_pattern(self):
        p = self.pattern.replace("\\\\", "X").replace("\{", "X").replace("\}", "X")
        findall = re.findall("[{]|[}]", p) # p does not contain escaped { or }
        if len(findall) == 2:
            if not re.search("[{][N]*[D]*[}]", p) or re.search("[{][}]", p):
                raise ValidationError(_("There is a syntax error in the barcode pattern") + " %s." % self.pattern)
        elif len(findall) != 0:
            raise ValidationError(_("There is a syntax error in the barcode pattern") + " %s." % self.pattern)