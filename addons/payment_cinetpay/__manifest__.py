{
    'name': 'CinetPay Payment Acquirer',
    'version': '1.0',
    'summary': 'Module de paiement Odoo via CinetPay',
    'description': """
Intégration du provider CinetPay pour les paiements en ligne dans Odoo.
Fonctionnalités :
- Paiement par carte bancaire / mobile money via CinetPay
- Gestion des transactions
- Gestion des callbacks
""",
    'author': 'AlainGansonré/ Sunsoft_Internationnal',
    'category': 'Accounting/Payment Acquirers',
    'depends': ['payment',],
    'data': [
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
        'views/payment_template.xml', 
    ],
   
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
