# -*- encoding: utf-8 -*-
##############################################################################

{
    "name": "Portugal - Digital signature",
    "version": "1.0",
    "category": "Localisation/Account",
    "description": """
        This module allows the OpenERP invoice system to add a digital signature in order to be certified by the
        Portuguese Tax Authority.
	Anyone interested in using this module adapted to the requirements of the Portuguese Tax Authority.
	Please contact to mail jjnf@communities.pt
    """,
    "author": "Communities - Comunicações, Lda",
    "depends": ["l10n_pt_saft", "sale", "account", "account_refund_original"],
    "data": [
        'views/report_saleorder.xml',
        'account_invoice_workflow.xml',  #'invoice_view.xml'
                    ],
    "demo": [],
    "installable": True,
    "active": True,
}

