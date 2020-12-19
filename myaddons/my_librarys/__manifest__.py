# -*- coding: utf-8 -*-
{
    'name': "我的图书馆",  # Module title
    'summary': "Manage books easily",  # Module subtitle phrase
    'description': """Long description""",  # You can also rst format
    'author': "Parth Gajjar",
    'website': "http://www.example.com",
    'category': 'Library',
    'version': '12.0.1',
    'depends': ['base_setup'],
    # This data files will be loaded at the installation (commented becaues file is not added in this example)
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/library_security.xml',
        'views/library_book.xml',
    ],
    # This demo data files will be loaded if db initialize with demo data (commented becaues file is not added in this example)
    # 'demo': [
    #     'demo.xml'
    # ],
}
