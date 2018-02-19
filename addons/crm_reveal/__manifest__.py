{
    'name': 'CRM Reveal',
    'summary': 'Create Lead/Opportunity from website visiters',
    'category': 'CRM',
    'depends': ['iap','crm','website', 'http_tracking'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/crm_view.xml',
        'views/crm_reveal_template.xml',
        'views/http_tracking_view.xml',
        'data/acquisition_rule_data.xml'
    ],
}
