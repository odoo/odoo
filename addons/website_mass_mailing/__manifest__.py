# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Newsletter Subscribe Button',
    'summary': 'Attract visitors to subscribe to mailing lists',
    'description': """
This module brings a new building block with a mailing list widget to drop on any page of your website.
On a simple click, your visitors can subscribe to mailing lists managed in the Email Marketing app.
    """,
    'version': '1.0',
    'category': 'Website/Website',
    'depends': ['website', 'mass_mailing', 'google_recaptcha'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_model_data.xml',
        'views/snippets/s_popup.xml',
        'views/snippets_templates.xml',
    ],
    'auto_install': ['website', 'mass_mailing'],
    'assets': {
        'web.assets_frontend': [
            'website_mass_mailing/static/src/scss/website_mass_mailing.scss',
            'website_mass_mailing/static/src/scss/website_mass_mailing_popup.scss',
            'website_mass_mailing/static/src/js/website_mass_mailing.js',
            'website_mass_mailing/static/src/xml/*.xml',
        ],
        'website.assets_wysiwyg': [
            'website_mass_mailing/static/src/js/website_mass_mailing.editor.js',
            'website_mass_mailing/static/src/js/mass_mailing_form_editor.js',
            'website_mass_mailing/static/src/scss/website_mass_mailing_edit_mode.scss',
            'website_mass_mailing/static/src/snippets/s_popup/options.js',
        ],
        'web.assets_tests': [
            'website_mass_mailing/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
