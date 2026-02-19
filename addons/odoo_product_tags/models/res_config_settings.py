# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from ast import literal_eval
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_tag_ids = fields.Many2many(
        'product.tag', string='Default Product Tags')

    def set_values(self):
        """ save values in the settings product tag fields"""
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            'odoo_product_tags.product_tag_ids',
            self.product_tag_ids.ids)
        return res

    @api.model
    def get_values(self):
        """ Get values for product tag fields in the settings
         and assign the value to that fields"""
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        pro_tag_ids = params.get_param(
            'odoo_product_tags.product_tag_ids')
        if pro_tag_ids:
            res.update(
                product_tag_ids=[(6, 0, literal_eval(
                    pro_tag_ids))] if pro_tag_ids else False)
            return res
        else:
            return res
