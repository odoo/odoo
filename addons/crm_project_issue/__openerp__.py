{
    'name' : 'CRM Project Issues',
    'version': '1.0',
    'summary': 'Module linker between Leads and Issues',
    'sequence': '19',
    'category': 'Project Management',
    'complexity': 'easy',
    'author': 'OpenERP SA',
    'description':
        """
CRM Project Issues
==================

Link module to map leads and issues
        """,
    'data': [
        'project_issue_view.xml'
    ],
    'depends' : ['crm', 'project_issue'],
    'installable': True,
}
