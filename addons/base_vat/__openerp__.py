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
{
    'name': 'Base VAT - To check VAT number validity',
    'version': '1.0',
    'category': 'Tools',
    'description': """Check the validity of VAT Numbers.
    Enable the VAT Number for the partner. 

    This module follows the methods stated at http://sima-pc.com/nif.php for
    checking the validity of VAT Number assigned to partners in European countries.
    """,
    'author': 'OpenERP SA',
    'depends': ['account'],
    'website': 'http://www.openerp.com',
    'update_xml': ['base_vat_view.xml'],
    'installable': True,
    'active': False,
    'certificate': '0084849360989',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
