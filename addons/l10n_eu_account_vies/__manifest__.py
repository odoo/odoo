{
    'name': 'VAT VIES Validation',
    'category': 'Accounting/Accounting',
    'description': """
VAT validation for Partner's VAT numbers.
=========================================

After installing this module, values entered in the VAT field of Partners will
be validated using VIES for all supported countries. The country is inferred from the
2-letter country code that prefixes the VAT number, e.g. ``BE0477472701``
will be validated using the Belgian rules.

    * When the "VAT VIES Check" option is enabled (in the configuration of the user's
      Company), VAT numbers will be submitted to the online EU VIES database,
      which will truly verify that the number is valid and currently
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
    'data': [
        'data/ir_cron.xml',
        'views/res_partner_views.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
