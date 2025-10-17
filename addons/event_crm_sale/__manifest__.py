# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event CRM Sale',
    'category': 'Marketing/Events',
    'website': 'https://www.odoo.com/app/events',
    'description': "Add information of sale order linked to the registration for the creation of the lead.",
    'depends': ['event_crm', 'event_sale'],
    'data': [
        'views/event_lead_rule_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
