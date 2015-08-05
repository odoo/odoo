{
    'name': "Lead Scoring",
    'category': "CRM",
    'version': "1.0",
    'depends': ['base', 'sales_team', 'marketing', 'website_crm'],
    'author': "Odoo S.A.",
    'description': """\
    Lead Scoring
===================

This module allows you to...
    - Track specific page view on your website.
    - Assign score on lead: sort your lead automatically and consider the more important at first.
    - Assign lead to salesteams: define your own filters and sort automatically your leads by saleteam.
    - Assign lead to salesmen: define filter by saleman and dispatch automatically your leads to the right saleman.
""",
    'data': [
        'views/website_crm_score.xml',
        'views/reporting.xml',
        'views/sales.xml',
        'views/marketing.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/website_crm_score_demo.xml',
    ],
    'installable': True,
    'application': False,
}
