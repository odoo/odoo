{
    'name': "WhatsApp in Marketing Automation",
    'version': "1.0",
    'summary': "Integrate WhatsApp in marketing campaigns",
    'category': "Marketing/Marketing Automation",
    'depends': [
        'marketing_automation',
        'whatsapp',
    ],
    'data': [
        'views/marketing_activity_data_templates.xml',
        'views/marketing_activity_views.xml',
        'views/whatsapp_template_views.xml',
        'views/marketing_campaign_views.xml',
        'views/marketing_participant_views.xml',
        'security/marketing_automation_whatsapp_security.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
