# coding: utf-8
# Copyright 2011-2015 Therp BV <https://therp.nl>
# Copyright 2016 Opener B.V. <https://opener.am>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'OpenUpgrade Records',
    'version': '10.0.1.0.0',
    'category': 'Migration',
    'author': 'Therp BV, Opener B.V., OCA (Odoo Community Association)',
    'website': 'https://github.com/oca/openupgrade',
    'data': [
        'views/openupgrade_record.xml',
        'views/comparison_config.xml',
        'views/analysis_wizard.xml',
        'views/generate_records_wizard.xml',
        'views/install_all_wizard.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'external_dependencies': {
        'python': ['openerplib', 'openupgradelib'],
    },
}
