{
    'name': 'VendAI Supplier Finance',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Finance',
    'summary': 'Buyer-backed supplier financing integrated into Purchase Orders',
    'description': '''
        VendAI Finance Module
        ====================
        Enable tripartite supplier financing:
        - Buyers offer financing to suppliers on Purchase Orders
        - Automatic credit scoring based on transaction history
        - Guaranteed repayment via invoice payment auto-split
        - Integration with Pezesha/Kuunda lending APIs
    ''',
    'author': 'VendAI',
    'website': 'https://vendai.digital',
    'depends': ['base', 'purchase', 'account', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/credit_facility_sequence.xml',
        'views/credit_facility_views.xml',
        'views/purchase_order_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
