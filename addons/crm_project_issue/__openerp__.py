# -*- coding: utf-8 -*-

{
    'name': 'Lead to Issue',
    'version': '1.0',
    'summary': 'Create Issues from Leads',
    'sequence': '19',
    'category': 'Project Management',
    'complexity': 'easy',
    'author': 'Odoo S.A.',
    'description': """
Lead to Issues
==============

Link module to map leads to issues
        """,
    'data': [
        'crm_lead2projectissue_wizard_views.xml'
    ],
    'depends': ['crm', 'project_issue'],
    'installable': True,
}
