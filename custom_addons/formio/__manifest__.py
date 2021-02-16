# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

{
    'name': 'Forms',
    'summary': 'Form Builder & integration of professional and versatile Forms to collect any information you need for your business.',
    'version': '8.17',
    'license': 'LGPL-3',
    'author': 'Nova Code',
    'website': 'https://www.novacode.nl',
    'live_test_url': 'https://demo13.novacode.nl',
    'category': 'Forms/Forms',
    'depends': ['web', 'portal', 'mail'],
    'qweb': [
        'static/src/xml/formio.xml',
    ],
    'data': [
        'data/formio_default_asset_css_data.xml',
        'data/formio_version_data.xml',
        'data/formio_version_asset_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_activity_data.xml',
        'data/mail_template_data.xml',
        # translations
        'data/formio_translations_sources.xml',
        'data/formio_translations_nl.xml',
        'data/formio_translations_nl_BE.xml',
        'data/formio_translations_pt_BR.xml',
        'data/formio_translations_zh_CN.xml',
        # security
        'security/formio_security.xml',
        'security/ir_model_access.xml',
        'security/ir_rule.xml',
        # views
        'views/formio_builder_views.xml',
        'views/formio_builder_js_options_views.xml',
        'views/formio_form_views.xml',
        'views/formio_res_model_views.xml',
        'views/formio_translation_source_views.xml',
        'views/formio_translation_views.xml',
        'views/formio_version_views.xml',
        'views/formio_version_github_tag_views.xml',
        'views/formio_menu.xml',
        'views/res_config_settings_views.xml',
        'views/mail_activity_views.xml',
        # formio templates
        'views/formio_builder_templates.xml',
        'views/formio_form_templates.xml',
        'views/formio_portal_templates.xml',
        'views/formio_public_templates.xml',
        # wizards
        'wizard/formio_version_github_checker_wizard.xml'
    ],
    'demo': [
        'data/formio_demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'images': [
        'static/description/banner.gif',
    ],
    'description': """
Forms
=====

Build, deploy and Forms.
"""
}
