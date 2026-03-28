# -*- coding: utf-8 -*-
{
    'name': "AI to SQL - Kodoo SQL Query Generator",
    'summary': "Gerador de Query SQL para Kodoo",
#    'summary': "AI TEXT2SQL for Odoo. Odoo AI SQL Generator and Data Export. AI to SQL Query. Model Context Protocol. SQL Query generation using LLM ChatGPT openai for AI data analytics.  chatbot, chat bot, odoo chatbot, odoo bot, odoo chat. ai chatbot, ai bot, ai chat. AI Search. MCP. Real-time SQL assistant provides realtime data. Unlock real-time Odoo data insights with an AI Analyst powered by ChatGPT technology. This Artificial Intelligence agent provides instant answers, acting as your personal data analytics assistant. Query sales, inventory, CRM, and more via natural language – information is just a prompt away. Get AI analytics and dashboard-like clarity without complex tools like Power BI or Tableau. Your Odoo AI for direct data exploration using your OpenAI key (compatible with models like Gemini via API). Get real time insights. Can be your powerbi or pbi, ai dashboard with KPI, copilot, odoo copilot, gemini, chat gpt, chatgpt, perplexity, n8n, AI reports. Works with openai chat gpt key. AI Agent, ml, Dashboard AI, AI Data Analytics, ai, ai odoo,  Provide realtime results and does not use cloud. Your data never leaver your Odoo server so no need of refresh or export, sync data daily. This is an AI Agent RAG like can answer any installed Odoo module query example sale, inventory, CRM, stock,customer,product,project,sales,invoices,order,invoices and more Niyu SQL AI. Data Export. SQL Data can be export to Excel spreadsheet. Artificial Intelligence used understands Odo Schema from Odo database. This AI Agent can understand users intent using LLM AI Model query database odoo database using odoo models and technical name and eliminates use of Odoo ORM. odoo analytics. odoo ai analytics, powerbi, power bi, power bi connector, powerbi connector, fabric connector, fabric, microsoft, microsoft fabric, spreadsheet, tablular respose shows data in table which can e downloaded. No data sync, nstant insights and realtime analytics. Useful for Odoo developer, ai analytics, excel connector, graph, chart, KPI, kpis, charts, graphs, plot, axis, ai data analytics, odoo data analyst, admin. relationship, entity, related column, chart, charts, kpi, dashboard, report, ai dashboard, ai report, sql connector, odoo sql connector, sql connection, odoo connector, ai connector.",
    'description': """
      Kodoo AI SQL Generator uses ChatGPT tech for AI data analytics. Ask questions, get Kodoo SQL queries. Real-time SQL assistant; see results, export data. Like AI dashboard  for your Kodoo database. Chat GPT AI agent for Kodoo AI. Your direct OpenAI key enables SQL exploration. No data sync, instant insights. Get Kodoo AI for SQL
    """,
    'author': "Niyu Labs",
    'website': "https://niyulabs.com", # Replace with actual
    'category': 'Productivity',
    'version': '19.0.1.0.0',
    'support': "info@niyulabs.com",
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
