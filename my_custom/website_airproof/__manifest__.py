{
    "name": "Website Airproof",
    "description": "A simple custom theme for Odoo website",
    "category": "Theme/Website",
    "version": "1.0",
    "author": "thang2k6adu",
    "depends": ["website"],
    "data": [
      'data/presets.xml',
      'views/website_templates.xml',
      'views/new_page_template_templates.xml',
      'data/menu.xml',
      'data/website_data.xml',
      'data/pages/about_us.xml',
      'data/pages/new_page_template_sections_airproof_faq.xml',
      'data/pages/profile.xml',
      'data/images.xml',
    ],
    "assets": {
      'web._assets_primary_variables': [
        'website_airproof/static/src/scss/primary_variables.scss',
      ],
      'web.assets_frontend': [
        'website_airproof/static/src/scss/font.scss',
        'website_airproof/static/src/scss/theme.scss',
        'website_airproof/static/src/js/theme.js',
        
      ],
      'web._assets_frontend_helpers': [
        ('prepend', 'website_airproof/static/src/scss/bootstrap_overridden.scss'),
      ],
    },
    'new_page_templates': {
      'airproof': {
        'faq': ['s_airproof_text_block_h1', 's_title', 's_faq_collapse', 's_call_to_action']
      }
    },
    "application": False,
    "installable": True,
    "license": "LGPL-3",
    "website_theme_install": True
}
