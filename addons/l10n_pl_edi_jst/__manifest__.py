{
    'name': 'Polish E-Invoicing FA(3) LGU support',
    'category': 'Accounting/Localizations',
    'summary': 'Support for Local Government Unit (LGU) in the FA(3) format',
    'description': """Export FA(3) compliant XML invoices and prepare for integration with KSeF.""",
    'data': [
        'views/res_partner_views.xml',
        'data/fa3_template.xml',
    ],
    'depends': [
        'l10n_pl',
        'l10n_pl_edi',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
