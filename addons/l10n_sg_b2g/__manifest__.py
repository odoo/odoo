{
    'name': "Singapore Business-to-Government E-Invoicing",
    'category': 'Accounting/Accounting',
    'description': """
E-Invoicing for Singapore Business-to-Government vendors in compliance with AGD requirements
    """,
    'depends': ['l10n_sg_ubl_pint', 'l10n_sg_sale_peppol'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/sale_order_views.xml',
        'views/account_move_views.xml',

        'security/ir.access.csv',

        'data/partner_tag_data.xml',
        'data/res.partner.csv',
        'data/l10n.sg.statutory.board.subbusiness.unit.csv',
        'data/account.payment.term.csv',
        'data/product_data.xml',
    ],
}
