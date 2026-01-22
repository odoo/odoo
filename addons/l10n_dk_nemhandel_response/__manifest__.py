{
    'name': "Nemhandel Business Response",
    'summary': "This module is used to send/receive responses to documents received/sent with Nemhandel",
    'description': """
In addition to the Nemhandel module, this enable the business level response mechanism for Nemhandel documents.
When sending a document, and if the counterpart also handles business responses, you will be able to
see if your document has been accepted or rejected.
When receiving a document, you will be able to send a rejection or approval of the received document.
    """,
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'depends': [
        'l10n_dk_nemhandel',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/nemhandel_response_views.xml',
        'wizard/nemhandel_rejection_wizard_view.xml',
    ],
    'license': 'LGPL-3',
    'auto_install': True,
}
