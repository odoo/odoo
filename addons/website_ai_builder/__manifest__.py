{
    'name': 'Website AI Builder',
    'summary': 'AI-powered website page editing via natural language prompts',
    'description': """
    Adds AI capabilities to the Odoo website builder, allowing users to edit
    page content (XHTML, CSS classes) through natural language prompts using
    the Ask AI agent system with dedicated website building tools.
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website', 'html_builder', 'ai'],
    'data': [
        'data/ir_actions_server_data.xml',
        'data/ai_topic_data.xml',
        'data/ai_composer_data.xml',
    ],
    'assets': {
        'website.website_builder_assets': [
            'website_ai_builder/static/src/builder/ai_builder_plugin.js',
            'website_ai_builder/static/src/builder/builder_patch.js',
            'website_ai_builder/static/src/xml/website_builder.xml',
        ],
    },
    'license': 'OEEL-1',
    'author': 'Odoo S.A.',
}
