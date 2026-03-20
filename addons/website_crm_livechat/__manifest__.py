# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Lead Livechat Sessions',
    'category': 'Website/Website',
    'summary': 'View livechat sessions for leads',
    'description': """ Adds a stat button on lead form view to access their livechat sessions.""",
    'depends': ['website_crm', 'website_livechat', 'crm_livechat'],
    'data': [
        'views/website_crm_lead_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
