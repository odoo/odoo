{
    'name': "HTML Builder",
    'summary': "Generic html builder",
    'description': """
    This addon contains a generic html builder application. It is designed to be
    used by the website builder and mass mailing editor.
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    'auto_install': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'html_editor', 'website'],

    'assets': {
        'web.assets_backend': [
            'html_builder/static/src/website_preview/**/*',
            'website/static/src/xml/website_form_editor.xml',
            # TODO Remove the module's form js - this is for testing.
            'website/static/src/js/send_mail_form.js',
            # TODO when moving options to website: load this from website
            # directly. This file is loaded in assets_wysiwyg in website, but we
            # need to load it here for html_builder.
            'website/static/src/xml/website.cookies_bar.xml',
        ],
        # this bundle is lazy loaded when the editor is ready
        'html_builder.assets': [
            ('include', 'web._assets_helpers'),

            'html_builder/static/src/bootstrap_overriden.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',

            'html_builder/static/src/**/*',
            ('remove', 'html_builder/static/src/website_preview/**/*'),
        ],
        'html_builder.inside_builder_style': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_primary_variables'),
            'web/static/src/scss/bootstrap_overridden.scss',
            'html_builder/static/src/**/*.inside.scss',
        ],
        'html_builder.assets_edit_frontend': [
            ('include', 'website.assets_edit_frontend'),
        ],
        'html_builder.iframe_add_dialog': [
            ('include', 'web.assets_frontend'),
            'html_builder/static/src/snippets/snippet_viewer.scss',
            'website/static/src/snippets/**/*.edit.scss',
        ],
        'web.assets_unit_tests': [
            'html_builder/static/tests/**/*',
            ('include', 'html_builder.assets'),
        ],
        'web.assets_frontend': [
            'html_builder/static/src/website_preview/website_builder_action.editor.scss',
        ],
    },
    'license': 'LGPL-3',
}
