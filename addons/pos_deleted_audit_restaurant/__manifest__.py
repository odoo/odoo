# -*- coding: utf-8 -*-
# Copyright Jbnegoc SPA (https://jbnegoc.com)

{
    'name': 'Auditoria Eliminados Pos Restaurante',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Auditoría de productos eliminados en el POS',
    'description': """
Audita eliminaciones de líneas y cantidades en el POS con justificación.
""",
    'author': 'Jbnegoc SPA',
    'website': 'https://jbnegoc.com',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'security/pos_deleted_audit_security.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/pos_deleted_justification_views.xml',
        'views/pos_deleted_product_audit_views.xml',
    ],
    'qweb': [
        'static/src/xml/pos_deleted_audit.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_deleted_audit_restaurant/static/src/js/pos_deleted_audit.js',
        ],
    },
    'installable': True,
    'application': False,
}
