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

Note also that you need to activate PDF A in order to be able to submit a Factur-X pdf on Chorus Pro: 
go to Settings > Technical (debug mode) > System Parameters > select/create one with Key: edi.use_pdfa, Value: true. 
With this setting, Chorus Pro will automatically detect the "PDF/A-3 (Factur-X)" format.
    """,
    'depends': ['account_edi'],
    'data': [
        'data/account_edi_data.xml',
        'data/cii_22_templates.xml',
        'data/ubl_20_templates.xml',
        'data/ubl_21_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
