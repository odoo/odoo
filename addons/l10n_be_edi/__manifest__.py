# -*- coding: utf-8 -*-
{
    'name': 'Belgium - E-Invoicing (UBL 2.0, e-fff)',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'E-Invoicing, Universal Business Language (UBL 2.0), e-fff protocol',
    'description': """
Universal Business Language (UBL <http://ubl.xml.org/>`_) is a library of standard electronic XML business documents such as
invoices. The UBL standard became the `ISO/IEC 19845
<http://www.iso.org/iso/catalogue_detail.htm?csnumber=66370>`_ standard in January 2016
(cf the `official announce <http://www.prweb.com/releases/2016/01/prweb13186919.htm>`_).
Belgian e-invoicing uses the UBL 2.0 using the e-fff protocol.
    """,
    'depends': ['l10n_be', 'account_edi_ubl'],
    'data': [
        'data/account_edi_data.xml'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
