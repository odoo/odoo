# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP SA (<http://www.openerp.com>).
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


{
    'name' : 'Account Product Template',
    'depends' : ['account'],
    'author' : 'OpenERP SA',
    'category': 'Accounting & Finance',
    'description': """
This module adds Product Template.
==================================

Whith this module, link your products to a template to send complete information and tools to your customer. For instance, you invoice a training, link a template to this training product with training agenda and materials.
    """,
    'website': 'http://www.openerp.com',
    'demo': [],
    'data': [
        'account_product_view.xml',
        'account_product_template_data.xml'
    ],
    'js': [],
    'css': [],
    'qweb' : [],
    'images': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
