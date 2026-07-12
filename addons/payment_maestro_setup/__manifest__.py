# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Configuração de Pagamentos (Stripe + Mercado Pago)',
    'version': '1.0',
    'category': 'Accounting/Payment',
    'summary': 'Wizard de configuração automática do Stripe e Mercado Pago em um único formulário',
    'depends': [
        'payment',
        'payment_stripe',
        'payment_mercado_pago',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/payment_setup_wizard_views.xml',
        'views/payment_setup_menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
