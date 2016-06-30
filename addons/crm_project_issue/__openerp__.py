{
    'name': 'Lead to Issue',
    'version': '1.0',
    'summary': 'Create Issues from Leads',
    'sequence': '19',
    'category': 'Project',
    'complexity': 'easy',
    'description': """
Lead to Issues
==============

Link module to map leads to issues
        """,
    'data': [
        'project_issue_view.xml'
    ],
    'depends': ['crm', 'project_issue'],
    'installable': True,
}
