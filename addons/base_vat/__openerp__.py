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
    'name': 'Base VAT',
    'version': '1.0',
    'category': 'Generic Modules/Base',
    'description': """
Enable VAT Number for a partner and check its validity.
=======================================================

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
    'images': ['images/1_partner_vat.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: