# -*- coding: utf-8 -*-
{
    'name': "School",  # Module's public name
    'version': '1.0',           # Module's version number
    'summary': 'A brief description of what this module does', # Short summary
    'description': """
        A longer description of the module, often with markdown.
    """,
    'author': "Your Company Name", # Author's name
    'website': "https://www.yourcompany.com", # Author's website
    'category': 'Uncategorized', # Module category (e.g., 'Sales', 'Accounting', 'Website')
    'depends': ['base','product'], # List of modules this module depends on (e.g., 'base', 'web')
    'data': [
        "security/ir.model.access.csv",
        "views/school_view.xml",
        "views/student_view.xml",
        "views/teacher_view.xml"
    ],
    'installable': True,     # Can be installed from the UI
    'application': True,     # Marks it as a full application (vs. a library/component)
    'auto_install': False,   # Automatically install if all dependencies met (rarely used)
    'license': 'LGPL-3',     # License type (e.g., 'LGPL-3', 'AGPL-3', 'OEEL-1')
}
