# -*- coding: utf-8 -*-
# © 2026 Jbnegoc SPA - Todos los derechos reservados
# Desarrollado por: Jbnegoc SPA
# Módulo: Auditoría de Eliminaciones en Punto de Venta

{
    'name': 'Auditoría Eliminados POS Restaurante',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Control y auditoría de productos eliminados en órdenes del POS',
    'description': """
        Auditoría de Eliminaciones en Punto de Venta
        ============================================

        Este módulo permite auditar y rastrear todos los productos que son eliminados
        de las órdenes en el Punto de Venta, tanto en tiendas como en restaurantes.

        Características principales:
        ---------------------------
        * Control de permisos por usuario para habilitar auditoría
        * Justificaciones predeterminadas configurables
        * Popup de justificación al eliminar productos
        * Registro detallado de eliminaciones con:
            - Número de pedido
            - Producto eliminado
            - Cantidad eliminada
            - Usuario que eliminó
            - Fecha y hora exacta
            - Justificación completa
        * Vista de reportes para gerentes
        * Control de acceso para eliminar registros de auditoría
        * Compatible con POS estándar y POS Restaurant

        Desarrollado por:
        ---------------
        Jbnegoc SPA - Todos los derechos reservados

        Soporte: info@jbnegoc.cl
    """,
    'author': 'Jbnegoc SPA',
    'website': 'https://www.jbnegoc.cl',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'pos_restaurant',  # Opcional pero recomendado para restaurantes
    ],
    'data': [
        # Seguridad (debe ir primero)
        'security/security.xml',
        'security/ir.model.access.csv',

        # Datos iniciales
        'data/pos_deletion_reason_data.xml',

        # Vistas
        'views/res_users_view.xml',
        'views/pos_deletion_reason_view.xml',
        'views/pos_audit_deleted_view.xml',
        'views/menu.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_audit_deleted_items/static/src/js/pos_audit.js',
            'pos_audit_deleted_items/static/src/xml/pos_audit.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
