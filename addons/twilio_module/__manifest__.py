{
    'name': "Insabhi Twilio Integration",
    'depends': ['base','crm', 'mail'],
    'data': [
        'data/system_parameter.xml',
        'security/ir.model.access.csv',
        'views/crm.xml',
        'views/res_company.xml',
        'views/twilio_message_log.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
