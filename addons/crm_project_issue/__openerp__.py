{
    'name': 'Lead to Issue',
    'version': '1.0',
    'summary': 'Create Issues from Leads',
    'sequence': '19',
    'category': 'Project Management',
    'complexity': 'easy',
    'description': """
Lead to Issues
==============

Link module to map leads to issues
        """,
    'data': [
        'wizard/crm_lead2projectissue_wizard_view.xml'
    ],
    'depends': ['crm', 'project_issue'],
    'installable': True,
}
