# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Argentinean Electronic Invoicing",
    'countries': ['ar'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'sequence': 14,
    'author': 'ADHOC SA',
    'description': """
Functional
----------

Be able to create journals in Odoo to create electronic customer invoices and report then to AFIP (via webservices).
The options available are:

    * Electronic Invoice - Web Service
    * Export Voucher - Web Service
    * Electronic Fiscal Bond - Web Service

In the electronic journals if you validate an invoice this one will be validated in both Odoo and AFIP. This validation is
made at the instant and we recieve and "approved/approved with observation/rejected" state from AFIP. If the invoice has
been rejected by AFIP will not be post in the system and a pop up message will be shown with both the error detail (reject reasons)
we recieve and a HINT about what the problem could be.

For auditing and troubleshooting purposes we also add a menu "Consulit Invoice in AFIP" that let us to consult invoices previously
sent to AFIP and last number used as support for any possible issues on the sequences synchronization between Odoo and AFIP.

    NOTE: From the Journal's form view we are able to force a sync between the odoo sequences to each of the document types in
    with the last numbers registered in AFIP.

From vendor bills, we have added a functionality that can be configured in the accounting settings to be able to verify
vendor bills in AFIP to check if the vendor bills are real (more information please review the setting description).

Configuration:

1. Go to the Accounting Settings > Argentinean Localization section

    1.1. Configure the AFIP Web Services mode:

    * Testing environment in order to use demo certificates that will be use to test the instance and to make NOT
      real invoices to AFIP. is just for testing. For demo instaces is already pre-defined you will not need to configure
      it (commonly named in AFIP as Homologation environment).
    * Production environment in order to generate real certificates and legal invoices to AFIP,

    1.2. Configure your AFIP Certificate: If you are in a demo instance this one will be have been set by default. If you
         are in production instance just need to go to upload your AFIP Certificate

    1.3. Optionally you can define if you like to be eable to verify vendor bills in AFIP.

2. Create Sales journals that will represent each one of your AFIP POS (Available in AFIP Portal) you want to use in Odoo.

    2.1. Use Documents field is set by default please dont change
    2.2. Set AFIP POS System for one of the electronic ones.

        * Electronic Invoice - Web Service'
        * Electronic Fiscal Bond - Web Service'
        * Export Voucher - Web Service'

    2.3. Set the AFIP POS Number and AFIP POS Address taking into account what you have configured in your AFIP Portal.

    NOTE: You can use the "Check Available AFIP POS" button in Journal's form to corroborate the to use to create the journals.

For more information about Argentinean Electronic invoicing please go to http://www.afip.gob.ar/fe/ayuda.asp

Technical
---------

The web services that are implemented are the ones that are the most common:

* wsfev1 - "Factura Electrónica" (Electronic Invoice)
* wsbfev1 - "Bono Fiscal Electrónico" (Electronic Fiscal Bond)
* wsfexv1 - "Factura de Exportación Electrónica" (Electronic Exportation Invoice - same as Export Voucher)
* wscdc - "Constatación de Comprobantes" (Invoices Verification)

For Development information go to http://www.afip.gob.ar/fe/documentos/WSBFEv1%20-%20Manual%20para%20el%20desarrollador.pdf

""",
    'depends': [
        'l10n_ar',
    ],
    'external_dependencies': {
        'python': ['pyOpenSSL', 'zeep']
    },
    'data': [
        'wizards/l10n_ar_afip_ws_consult_view.xml',
        'views/l10n_ar_afipws_connection_view.xml',
        'views/res_config_settings_view.xml',
        'views/account_move_view.xml',
        'views/account_journal_view.xml',
        'views/res_currency_view.xml',
        'views/product_template_view.xml',
        'views/report_invoice.xml',
        'security/ir.model.access.csv',
        'data/ir_actions_act_url_data.xml',
    ],
    'demo': [
        'demo/res_company_demo.xml',
        'demo/res_config_settings_demo_view.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_ar'],
    'license': 'OEEL-1',
}
