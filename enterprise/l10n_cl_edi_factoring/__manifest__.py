{
    'name': 'Chile - Localization: Factoring Extension',
    'countries': ['cl'],
    'version': '1.0',
    'category': 'Localization/Chile',
    'description': '''
E-Invoice Factoring
===================
This module is an extension for chilean electronic invoicing.
It creates the electronic file (Archivo Electrónico de Cesión de créditos - AEC), in order to yield the credit of
the invoices to a factoring company.
It also creates an account entry to have the invoice paid-off and translate the credit to the factoring company.
Additionally, it marks the invoice as 'yielded' in the payment state.
    ''',
    'author': 'Blanco Martin y Asociados',
    'website': 'https://www.bmya.cl',
    'license': 'OEEL-1',
    'depends': [
        'l10n_cl_edi',
    ],
    'data': [
        'template/aec_template.xml',
        'views/account_move_view.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_view.xml',
        'wizard/l10n_cl_aec_generator_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/partner_demo.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_cl_edi'],
    'post_init_hook': 'post_init_hook',
}
