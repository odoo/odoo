# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "payment_adyen_paybylink",
    'category': 'Accounting/Payment',
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'version': '1.0',
    'description': """
        Long description of module's purpose
    """,
    'depends': ['payment_adyen'],
    'data': [
        'views/payment_views.xml',
    ],
}
