# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": """Electronic Exports of Goods for Chile""",
    'countries': ['cl'],
    'version': '1.0',
    'category': 'Localization/Chile',
    'description': '''
Even when the quantity of packages is apparently only inherent to stock application, we need a field for this
in the invoice, because that info could also depend on the DUS declaration.
We should also consider that there may be users without the inventory application installed and keep a less
complex logic.
''',
    'sequence': 12,
    'author':  'Blanco Martin y Asociados',
    'website': 'https://www.bmya.cl',
    'license': 'OEEL-1',
    'depends': [
        'l10n_cl_edi',
    ],
    'data': [
            'views/account_move_view.xml',
            'views/l10n_cl_customs_port_view.xml',
            'views/report_invoice.xml',
            'template/dte_template.xml',
            'security/ir.model.access.csv',
            'data/account_incoterm_data.xml',
            'data/l10n_cl.customs_port.csv',
    ],
    'installable': True,
}
