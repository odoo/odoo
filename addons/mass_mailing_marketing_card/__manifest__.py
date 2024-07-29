{
    'name': 'Cards Mailing',
    'summary': 'Design and send shareable cards',
    'version': '1.0',
    'category': 'Marketing/Email Marketing',
    'depends': [
        'mass_mailing',
        'marketing_card',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/snippets/s_call_to_share_card.xml',
        'views/snippets/snippets.xml',
    ],
    'assets': {
        'web_editor.backend_assets_wysiwyg': [
            'mass_mailing_marketing_card/static/src/js/mass_mailing_wysiwyg.js',
        ],
        'mass_mailing.assets_snippets_menu': [
            'mass_mailing_marketing_card/static/src/js/snippets.editor.js'
        ],
        'mass_mailing.assets_wysiwyg': [
            'mass_mailing_marketing_card/static/src/snippets/s_call_to_share_card/options.js',
        ],
        'web.assets_backend': [
            'mass_mailing_marketing_card/static/src/js/mass_mailing_html_field.js',
        ],
    },
}
