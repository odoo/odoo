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
    'name': 'VAT Number Validation',
    'version': '1.0',
    'category': 'Hidden/Dependency',
    'description': """
VAT validation for Partner's VAT numbers.
=========================================

After installing this module, values entered in the VAT field of Partners will
be validated for all supported countries. The country is inferred from the
2-letter country code that prefixes the VAT number, e.g. ``BE0477472701``
will be validated using the Belgian rules.

There are two different levels of VAT number validation:
--------------------------------------------------------
    * By default, a simple off-line check is performed using the known validation
      rules for the country, usually a simple check digit. This is quick and 
      always available, but allows numbers that are perhaps not truly allocated,
      or not valid anymore.
      
    * When the "VAT VIES Check" option is enabled (in the configuration of the user's
      Company), VAT numbers will be instead submitted to the online EU VIES
      database, which will truly verify that the number is valid and currently
      allocated to a EU company. This is a little bit slower than the simple
      off-line check, requires an Internet connection, and may not be available
      all the time. If the service is not available or does not support the
      requested country (e.g. for non-EU countries), a simple check will be performed
      instead.

Supported countries currently include EU countries, and a few non-EU countries
such as Chile, Colombia, Mexico, Norway or Russia. For unsupported countries,
only the country code will be validated.
    """,
    'author': 'OpenERP SA',
    'depends': ['account'],
    'website': 'https://www.odoo.com/page/accounting',
    'data': ['base_vat_view.xml'],
    'installable': True,
    'auto_install': False,
    'images': ['images/1_partner_vat.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
