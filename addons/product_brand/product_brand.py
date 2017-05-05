# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# product_brand for Odoo                                                      #
# Copyright (C) 2009 NetAndCo (<http://www.netandco.net>).                    #
# Copyright (C) 2011 Akretion Benoît Guillot <benoit.guillot@akretion.com>    #
# Copyright (C) 2014 prisnet.ch Seraphine Lantible <s.lantible@gmail.com>     #
# Copyright (C) 2015 Leonardo Donelli                                         #
# Contributors                                                                #
# Mathieu Lemercier, mathieu@netandco.net                                     #
# Franck Bret, franck@netandco.net                                            #
# Seraphine Lantible, s.lantible@gmail.com, http://www.prisnet.ch             #
# Leonardo Donelli, donelli@webmonks.it, http://www.wearemonk.com             #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as              #
# published by the Free Software Foundation, either version 3 of the          #
# License, or (at your option) any later version.                             #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                #
# GNU Affero General Public License for more details.                         #
#                                                                             #
# You should have received a copy of the GNU Affero General Public License    #
# along with this program. If not, see <http://www.gnu.org/licenses/>.        #
#                                                                             #
###############################################################################
###############################################################################
# Product Brand is an Openobject module wich enable Brand management for      #
# products                                                                    #
###############################################################################
from openerp import models, fields, api


class ProductBrand(models.Model):
    _name = 'product.brand'

    name = fields.Char('Brand Name', required=True)
    description = fields.Text('Description', translate=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help='Select a partner for this brand if it exists',
        ondelete='restrict'
    )
    logo = fields.Binary('Logo File')
    product_ids = fields.One2many(
        'product.template',
        'product_brand_id',
        string='Brand Products',
    )
    products_count = fields.Integer(
        string='Number of products',
        compute='_get_products_count',
    )

    @api.one
    @api.depends('product_ids')
    def _get_products_count(self):
        self.products_count = len(self.product_ids)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        help='Select a brand for this product'
    )
