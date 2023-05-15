# -*- coding: utf-8 -*-
{
    'name': "Import/Export electronic invoices with UBL/CII",
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Electronic invoicing module
===========================

Allows to export and import formats: E-FFF, UBL Bis 3, EHF3, NLCIUS, Factur-X (CII), XRechnung (UBL).
When generating the PDF on the invoice, the PDF will be embedded inside the xml for all UBL formats. This allows the
receiver to retrieve the PDF with only the xml file. Note that **EHF3 is fully implemented by UBL Bis 3** (`reference
<https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/#_implementation>`_).

The formats can be chosen from the journal (Journal > Advanced Settings) linked to the invoice.

Note that E-FFF, NLCIUS and XRechnung (UBL) are only available for Belgian, Dutch and German companies,
respectively. UBL Bis 3 is only available for companies which country is present in the `EAS list
<https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/>`_.

Note also that in order for Chorus Pro to automatically detect the "PDF/A-3 (Factur-X)" format, you need to activate
the "Factur-X PDF/A-3" option on the journal. This option will also validate the xml against the Factur-X and Chorus
Pro rules and show the errors.
    """,
    'depends': ['account'],
    'data': [
        'data/cii_22_templates.xml',
        'data/ubl_20_templates.xml',
        'data/ubl_21_templates.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_send_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
