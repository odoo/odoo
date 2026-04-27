{
    "name": "Uruguay - Electronic Invoice",
    "countries": ["uy"],
    "category": "Accounting/Localizations/EDI",
    "license": "OEEL-1",
    "version": "1.0",
    "description": """
This module integrate Odoo so you can issue electronic documents (CFE) to DGI. Example: e-Ticket, e-Invoice and related Debit and Credit Notes.

After the CFE has been issued, and since the invoice validation is asynchronous, Odoo will run a scheduled action that will connect to DGI to check/update CFE state (Waiting DGI Response, Approved or Rejected)

NOTE: Every connection is made using a third-party software named Uruware

Configuration
-------------

1. Need to have an Uruguayan Company (with the Uruguayan COA installed)
2. Go to Settings / Accounting / Uruguay Localization section and configure the fields to connect to UCFE: Uruware's platform for connecting to the Dirección General Impositiva (DGI)
3. Go to Settings / Users / Companies / Companies and set the Tax ID number, DGI Main House or Branch Code, all your Address related  fields.
4. Go to Invoices and validate them. Then use Send and Print to send to the government and generate a CFE. You will see a new field "CFE Status" that will show you the status of the electronic document: initially, it will be in "Waiting DGI response", and after some time it will be automatically updated to Approved/Rejected. You will also receive the legal PDF and XML files related to the CFE as attachments to the document.

Known issues / Roadmap
======================

* Contingency documents not implemented
* Future implementation will have auto synchronization of Vendor bills.
    """,
    "author": "ADHOC SA",
    "depends": [
        "l10n_uy",
    ],
    "data": [
        "views/account_journal_views.xml",
        "views/account_move_views.xml",
        "views/l10n_uy_edi_addenda_views.xml",
        "views/l10n_uy_edi_document_views.xml",
        "views/res_config_settings_view.xml",
        "views/res_company_views.xml",
        "views/report_invoice.xml",
        "views/cfe_template.xml",
        "data/ir_cron.xml",
        "data/res_currency_data.xml",
        "security/ir.model.access.csv",
        "security/security.xml",
    ],
    "demo": [
        "demo/l10n_uy_edi_addenda_demo.xml",
        "demo/res_currency_rate_demo.xml",
    ],
    "installable": True,
}
