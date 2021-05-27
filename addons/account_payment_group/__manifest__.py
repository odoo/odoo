# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account Payment with Multiple methods",
    "Description": "Account Payment with Multiple methods",
    "version": "1.0.0",
    "category": "Accounting",
    "website": "www.adhoc.com.ar",
    "author": "ADHOC SA",
    "license": "AGPL-3",
    "application": False,
    'installable': True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "account",
    ],
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_payment_group_view.xml',
        'views/account_payment_view.xml',
        'views/report_payment_group.xml',
        'data/ir_sequence_data.xml',
        'data/ir_actions_server_data.xml',
    ],
    "demo": [
    ],
}
