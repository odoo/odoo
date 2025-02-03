# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indian - Online Event Ticketing',
    'countries': ['in'],
    'description': """ Sell online tickets for Indian Events """,
    'category': 'Marketing/Events',
    'depends': [
        'website_event_sale',
        'l10n_in_sale',
    ],
    'auto_install': True,
    'data': [
        'views/event_event_views.xml',
    ],
    'license': 'LGPL-3',
}
