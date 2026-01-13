{
    'name': "Peppol Business Response",
    'summary': "This module is used to send/receive responses to documents received/sent with PEPPOL",
    'description': """
In addition to the PEPPOL module, this enable the business level response mechanism for PEPPOL documents.
When sending a document, and if the counterpart also handles business responses, you will be able to
see if your document has been accepted or rejected.
When receiving a document, you will be able to send a rejection or approval of the received document.
    """,
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': [
        'account_peppol',
    ],
    'data': [
        'data/cron.xml',
        'data/peppol_clarification_data.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_peppol_response_views.xml',
        'wizard/peppol_rejection_wizard_view.xml',
    ],
    'post_init_hook': '_account_peppol_response_post_init',
    'uninstall_hook': '_account_peppol_response_uninstall',
    'license': 'LGPL-3',
    'auto_install': True,
}
