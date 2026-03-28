{
    'name': 'Cobalt Theme',
    'description': 'Clean and sharp design.',
    'category': 'Theme/Corporate',
    'summary': 'Development, IT development, Design, Tech, Computers, IT, Blogs',
    'sequence': 110,
    'version': '2.0.0',
    'depends': ['website'],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/images.xml',
        'views/customizations.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/cobalt_poster.webp',
        'static/description/cobalt_screenshot.webp',
    ],
    'configurator_snippets': {
        'homepage': ['s_banner', 's_image_text', 's_key_images', 's_text_image', 's_company_team_detail', 's_references_grid'],
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_banner'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'data_attributes': {
                'gap': '3',
                'alignment': 'right',
            },
            'background': {
                'color': 'o_cc2',
            },
            'add_classes': [
                'pt48', 'pb48',
            ],
            'remove_classes': [
                'pt64', 'pb64', 's_dynamic_category_no_arrows',
            ],
        },
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.assets_editor': [
            'theme_cobalt/static/src/js/tour.js',
        ],
    }
}
