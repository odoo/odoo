{
    'name': 'Chatbot Addon',
    'version': '1.0',
    'summary': 'A chatbot that connects to OpenAI or a self-hosted model',
    'author': '',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/categories.xml',
        'views/chatbot_views.xml',
    ],
    'installable': True,
    'application': True,
}
