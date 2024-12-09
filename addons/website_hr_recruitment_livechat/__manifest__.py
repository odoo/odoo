{
    'name': 'HR Recruitment Live Chat',
    'category': 'Hidden',
    'summary': 'Chatbot for the HR Recruitment',
    'version': '1.0',
    'description': """
A chatbot to help the user be guided through recruitment process on the website and land on the right jobs position.
    """,
    'depends': ['website_hr_recruitment', 'im_livechat'],
    'installable': True,
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'security/website_hr_recruitment_livechat.xml',
        'data/website_hr_recruitment_livechat_chatbot_demo_data.xml',
    ],
    'demo': [
        'data/website_hr_recruitment_livechat_chatbot_demo.xml',
    ],
    'license': 'LGPL-3',
}
