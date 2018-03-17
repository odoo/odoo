{
    'name': 'School Application',
    'version': '10.0.1.0.13',
    'author': '''Francis Bangura. <francisbnagura@gmail.com>''',
    'website': 'https://www.byteltd.com/',
    'images': ['static/description/school.png'],
    'category': 'School Management',
    'license': "AGPL-3",
    'complexity': 'easy',
    'Summary': 'A Module For School Application Process',
    'depends': ['school'],
    'data': [#'security/school_security.xml',
             #'security/ir.model.access.csv',
             'views/school_application_view.xml',
             'views/school_settings.xml',
             'data/application_sequence.xml',
             ],
    'demo': [
        #'demo/school_demo.xml'
    ],
    #'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True
}
