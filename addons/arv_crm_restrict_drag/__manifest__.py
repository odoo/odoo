# -*- coding: utf-8 -*-
{
    'name': 'Won Stage Drag Restriction | Kanban Drag Restriction for Won Stages | Lead Drag',
    'version': '16.0.1',
    'author': 'Aravind S',
    'website': 'aravinds.odoo.com',
    'support': 'aravindu28@gmail.com',
    'category': 'Services/Tools',
    'summary': 'This module provides a simple solution to prevent dragging of records in Kanban views when they are in a "won" stage.',
    'description': 'This module provides a simple solution to prevent dragging of records in Kanban views when they are in a "won" stage. In many business workflows, once a record has reached a "won" stage, it should no longer be moved or modified. This module ensures data integrity and workflow consistency by restricting the ability to drag such records within the Kanban view.',
    "depends": ['crm'],
    "assets": { "web.assets_backend": [ "arv_crm_restrict_drag/static/src/**/*" ] },
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'images': ['static/description/thumbnail.gif'],
}
