

{
    'name': 'Account - Intrastat Declaration',
    'version': '11.0.1.0.0',
    'category': 'Account',
    'description': """
    Intrastat Declaration and export file.
    """,
    'author': 'Openforce'
        ', Link IT srl',
    'website': 'http://linkgroup.it/',
    'license': 'Other proprietary',
    "depends": [
        'l10n_it_intrastat',
        ],
    "data": [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'wizard/export_file_view.xml',
        'views/config.xml',
        'views/intrastat.xml',
        ],
    "demo": [],
    "installable": True
}

