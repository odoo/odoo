# -*- encoding: utf-8 -*-
###############################################################################
# #                                                                           #
# product_brand for Odoo #                                                    #
# Copyright (C) 2009 NetAndCo (<http://www.netandco.net>). #                  #
# Copyright (C) 2011 Akretion Benoît Guillot <benoit.guillot@akretion.com> #  #
# Copyright (C) 2014 prisnet.ch Seraphine Lantible <s.lantible@gmail.com> #   #
# Contributors                                                                #
# Mathieu Lemercier, mathieu@netandco.net, #                                  #
# Franck Bret, franck@netandco.net #                                          #
# Seraphine Lantible, s.lantible@gmail.com, http://www.prisnet.ch             #
# #                                                                           #
# This program is free software: you can redistribute it and/or modify #      #
# it under the terms of the GNU Affero General Public License as #            #
# published by the Free Software Foundation, either version 3 of the #        #
# License, or (at your option) any later version. #                           #
# #                                                                           #
# This program is distributed in the hope that it will be useful, #           #
# but WITHOUT ANY WARRANTY; without even the implied warranty of #            #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the #              #
# GNU Affero General Public License for more details. #                       #
# #                                                                           #
# You should have received a copy of the GNU Affero General Public License #  #
# along with this program. If not, see <http://www.gnu.org/licenses/>. #      #
# #                                                                           #
###############################################################################
###############################################################################
# Product Brand is an Openobject module wich enable Brand management for      #
# products                                                                    #
###############################################################################
{
    'name': 'Product Brand Manager',
    'version': '0.1',
    'category': 'Product',
    'summary': 'Add brand to products',
    'author': 'NetAndCo, Akretion, Prisnet Telecommunications SA'
              ', MONK Software, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'depends': ['product'],
    'data': [
        'product_brand_view.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
}
