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
        'name': fields.char('Nomenclature Name', size=32, required=True, help='An internal identification of the barcode nomenclature'),
        'rule_ids': fields.one2many('barcode.rule','barcode_nomenclature_id','Rules', help='The list of barcode rules'),
        'strict_ean': fields.boolean('Use strict EAN13', 
            help='Many barcode scanners strip the leading zero of EAN13 barcodes. By using strict EAN13, we consider the scanned barcode directly. Otherwise, we prepend scanned barcodes of length 12 by a zero before looking for the associated item.')
    }

    _defaults = {
        'strict_ean': False,
    }

    def use_strict_ean(self):
        return self.strict_ean

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

    # returns true if the barcode is a valid EAN barcode
    def check_ean(self, ean):
       return re.match("^\d+$", ean) and self.ean_checksum(ean) == int(ean[len(ean)-1])
        
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

        def match_pattern(barcode, pattern):
            match = {
                "value": 0,
                "base_code": barcode,
                "match": False,
            }

            barcode = barcode.replace("\\", "\\\\").replace("{", '\{').replace("}", "\}").replace(".", "\.")
            numerical_content = re.search("[{][N]*[D]*[}]", pattern)

            if numerical_content:
                num_start = numerical_content.start()
                num_end = numerical_content.end()
                value_string = barcode[num_start:num_end-2]

                whole_part_match = re.search("[{][N]*[D}]", numerical_content.group())
                decimal_part_match = re.search("[{N][D]*[}]", numerical_content.group())
                whole_part = value_string[:whole_part_match.end()-2]
                decimal_part = "0." + value_string[decimal_part_match.start():decimal_part_match.end()-1]
                if whole_part == '':
                    whole_part = '0'
                match['value'] = int(whole_part) + float(decimal_part)

                match['base_code'] = barcode[:num_start] + (num_end-num_start-2)*"0" + barcode[num_end-2:] 
                match['base_code'] = match['base_code'].replace("\\\\", "\\").replace("\{", "{").replace("\}","}").replace("\.",".")
                pattern = pattern[:num_start] + (num_end-num_start-2)*"0" + pattern[num_end:] 

            match['match'] = re.match(pattern, match['base_code'][:len(pattern)])

            return match


        rules = []
        for rule in self.rule_ids:
            rules.append({'type': rule.type, 'encoding': rule.encoding, 'sequence': rule.sequence, 'pattern': rule.pattern, 'alias': rule.alias})

        # If the nomenclature does not use strict EAN, prepend the barcode with a 0 if it seems
        # that it has been striped by the barcode scanner, when trying to match an EAN13 rule
        prepend_zero = False
        if not self.strict_ean and len(barcode) == 12 and self.check_ean("0"+barcode):
            prepend_zero = True

        for rule in rules:
            cur_barcode = barcode
            if prepend_zero and rule['encoding'] == "ean13":
                cur_barcode = '0'+cur_barcode

            match = match_pattern(cur_barcode, rule['pattern'])
            if match['match']:
                if rule['type'] == 'alias':
                    barcode = rule['alias']
                    parsed_result['code'] = barcode
                else:
                    parsed_result['encoding'] = rule['encoding']
                    parsed_result['type'] = rule['type']
                    parsed_result['value'] = match['value']
                    parsed_result['code'] = cur_barcode
                    if rule['encoding'] == "ean13":
                        parsed_result['base_code'] = self.sanitize_ean(match['base_code'])
                    else:
                        parsed_result['base_code'] = match['base_code']
                    return parsed_result

        return parsed_result

class barcode_rule(models.Model):
    _name = 'barcode.rule'
    _order = 'sequence asc'

    @api.model
    def _get_type_selection(self):
        return [('alias','Alias'),('product','Unit Product')]
        
    _columns = {
        'name':     fields.char('Rule Name', size=32, required=True, help='An internal identification for this barcode nomenclature rule'),
        'barcode_nomenclature_id':     fields.many2one('barcode.nomenclature','Barcode Nomenclature'),
        'sequence': fields.integer('Sequence', help='Used to order rules such that rules with a smaller sequence match first'),
        'encoding': fields.selection([('any','Any'),('ean13','EAN-13')],'Encoding',required=True,help='This rule will apply only if the barcode is encoded with the specified encoding'),
        'type':     fields.selection('_get_type_selection','Type', required=True),
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
            if not re.search("[{][N]*[D]*[}]", p):
                raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": braces can only contain N's followed by D's."))
            elif re.search("[{][}]", p):
                raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": empty braces."))
        elif len(findall) != 0:
            raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": a rule can only contain one pair of braces."))