# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Shonima (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, fields, models


class ProductTemplate(models.Model):
    """Inherited product.template class to add fields and functions"""
    _inherit = 'product.template'

    is_auto_generate = fields.Boolean(string="Is Auto Generate",
                                      compute='_compute_is_auto_generate',
                                      help="Used to hide and show the prefix "
                                           "and digit field based on the "
                                           "option that we choose in settings")
    prefix = fields.Char(string='Prefix',
                         help="Prefix value of the record for sequence")
    digits = fields.Integer(string='Digits',
                            help="Used to set number of digits contain in a "
                                 "sequence")
    number_next = fields.Integer(string='Next call', help="Next number that "
                                                          "will be used. This "
                                                          "number can be"
                                                          "incremented "
                                                          "frequently so the "
                                                          "displayed value "
                                                          "might"
                                                          "already be obsolete")

    @api.onchange('prefix', 'digits')
    def onchange_digits_prefix(self):
        """ This function is used to set number_next to zero if we change the
        prefix or digits"""
        self.number_next = 0

    def check_string_for_nine(self, string):
        """This function used to check whether the given string contain only '9'
         then it will return true else it returns false"""
        return all(char == '9' for char in string)

    def _number_next_actual(self):
        """This function used to generate the sequence number"""
        if self.is_auto_generate:
            number_next = self.number_next + 1
            self.number_next = number_next
            if (len(str(self.digits)) == len(str(self.number_next)) and
                    self.check_string_for_nine(str(self.number_next))):
                self.digits = self.digits + 1
            if self.digits - len(str(self.number_next)) <= 0:
                value = self.prefix
            else:
                digits = ("{:%s}" % ('0%sd' % str(self.digits - len(
                    str(self.number_next))))).format(0)
                value = self.prefix + digits
            return value + str(number_next)

    @api.depends('tracking')
    def _compute_is_auto_generate(self):
        """This function is used to set value to the field 'is_auto_generate'
        based on the value that we choose in
        settings page"""
        for rec in self:
            rec.is_auto_generate = False
            product_type = rec.env['ir.config_parameter'].sudo().get_param(
                'auto_generate_lot_number.serial_number_type')
            auto_generate = rec.env['ir.config_parameter'].sudo().get_param(
                'auto_generate_lot_number.is_auto_generate')
            if product_type == 'product' and auto_generate:
                rec.is_auto_generate = True

    def write(self, values):
        """This function is used to set 'number_next' to zero"""
        res = super(ProductTemplate, self).write(values)
        if values.get('prefix') or values.get('digits'):
            self.number_next = 0
        return res
