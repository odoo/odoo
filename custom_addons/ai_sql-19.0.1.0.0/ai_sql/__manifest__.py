# -*- coding: utf-8 -*-
{
    'name': "AI to SQL - Kodoo SQL Query Generator",
    'summary': "Gerador de Query SQL para Kodoo",
    'description': """
      Kodoo AI SQL Generator uses ChatGPT tech for AI data analytics. Ask questions, get Kodoo SQL queries. Real-time SQL assistant; see results, export data. Like AI dashboard  for your Kodoo database. Chat GPT AI agent for Kodoo AI. Your direct OpenAI key enables SQL exploration. No data sync, instant insights. Get Kodoo AI for SQL
    """,
    'author': "Niyu Labs",
    'website': "https://kodoo.online", # Replace with actual
    'category': 'Productivity',
    'version': '19.0.1.0.0',
    'support': "info@kodoo.online",
    'live_test_url': 'https://youtu.be/b7Z63-2Xh4U',
    'price': 0,
    'currency': 'USD',
    'images': ['static/description/banner.gif'],
    'license': 'OPL-1',
    'depends': ['base', 'web'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sql_generator_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Core OWL libraries are usually included by default if Owl component is used correctly
            'ai_sql/static/src/owl_components/sql_generator_view/sql_generator_view.js',
            'ai_sql/static/src/owl_components/sql_generator_view/sql_generator_view.xml',
            # 'ai_sql/static/src/sql_generator_view.scss',
        ],
    },
    'external_dependencies': {
        'python': ['requests', 'xlsxwriter'],
    },
    'application': True,
    'installable': True,
}
