{
    'name': 'ABA PayWay Base Configuration',
    'countries': ['KH'],
    'version': '1.0',
    # hiddeen/tool
    'category': 'Accounting/Payment',
    'summary': 'Base module to configure your API keys and connect ABA PayWay to Odoo.',
    'description': """
        This is the base module to set up ABA PayWay in Odoo. \n
        Add your API key, switch between sandbox and live mode, and manage your payment settings.

        To get started: \n
        Go to Contacts → Configuration → Bank Accounts, choose the bank account you want to accept payments with, then fill in your API Key and Merchant ID as provided by ABA PayWay.

        Need a Sandbox account? `Register here <https://sandbox.payway.com.kh/login/>`_
    """,
    'author': 'Odoo S.A., ABA Bank',
    'depends': [
        'l10n_kh',
    ],
    'auto_install': True,
    'data': [
        'views/res_bank.xml',
    ],
    'license': 'LGPL-3',
}
