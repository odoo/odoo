# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Base Validator',
    'version': '12.0.1.0.0',
    'category': 'Tools',
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'description': """
This module allows to set a python expression as value validator.
This module is intended to be extended by others and should not be installed
alone.

To use this module, you need to:

* Depend on this module
* Create new records for new validations
* Call validation from where you need
""",
    'depends': [
    ],
    'data': [
        'views/base_validator_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/base_validator.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
