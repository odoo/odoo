# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'VAT Number Validation',
    'version': '1.0',
    'category': 'Accounting',
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
    'depends': ['account'],
    'website': 'https://www.odoo.com/page/accounting',
    'data': ['base_vat_view.xml'],
    'installable': True,
    'auto_install': False,
}
