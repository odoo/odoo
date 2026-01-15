# -*- coding: utf-8 -*-
# © 2026 Jbnegoc SPA - Todos los derechos reservados
# Desarrollado por: Jbnegoc SPA

from odoo import api, fields, models, _


class PosOrder(models.Model):
    """
    Extensión del modelo pos.order para integrar la auditoría de eliminaciones.

    Se agregan campos computados y métodos para facilitar la trazabilidad
    de productos eliminados en cada pedido.
    """
    _inherit = 'pos.order'

    # Contador de productos eliminados en este pedido
    deleted_items_count = fields.Integer(
        string='Productos Eliminados',
        compute='_compute_deleted_items_count',
        help='Cantidad de registros de auditoría de eliminaciones '
             'asociados a este pedido'
    )

    # Relación inversa con los registros de auditoría
    audit_deleted_ids = fields.One2many(
        'pos.audit.deleted',
        'pos_order_id',
        string='Auditorías de Eliminación',
        help='Registros de auditoría de productos eliminados'
    )

    @api.depends('audit_deleted_ids')
    def _compute_deleted_items_count(self):
        """
        Computa la cantidad de productos eliminados en este pedido.
        """
        for order in self:
            order.deleted_items_count = len(order.audit_deleted_ids)

    def action_view_deleted_items(self):
        """
        Acción para ver los productos eliminados de este pedido.
        Abre una vista de lista filtrada con los registros de auditoría.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Productos Eliminados'),
            'res_model': 'pos.audit.deleted',
            'view_mode': 'tree,form',
            'domain': [('pos_order_id', '=', self.id)],
            'context': {
                'default_pos_order_id': self.id,
                'default_pos_order_name': self.name,
            },
        }

    @api.model
    def _order_fields(self, ui_order):
        """
        Sobrescribe el método _order_fields para procesar los registros
        de auditoría que vienen desde el frontend del POS.

        Este método se llama cuando se crea una orden desde la UI del POS.
        """
        order_fields = super(PosOrder, self)._order_fields(ui_order)

        # Procesar los registros de auditoría si existen
        if 'audit_deleted_items' in ui_order:
            audit_items = ui_order['audit_deleted_items']
            if audit_items:
                # Los registros de auditoría se crearán directamente
                # desde el JavaScript después de crear la orden
                pass

        return order_fields

    @api.model
    def create_audit_records_from_ui(self, order_id, audit_items):
        """
        Crea registros de auditoría desde el frontend del POS.

        :param order_id: ID del pedido al que se asociarán los registros
        :param audit_items: lista de dict con la información de eliminaciones
        :return: lista de IDs de registros creados
        """
        order = self.browse(order_id)
        audit_model = self.env['pos.audit.deleted']
        created_ids = []

        for item in audit_items:
            # Preparar valores para el registro de auditoría
            vals = {
                'pos_order_id': order.id,
                'pos_order_name': order.pos_reference or order.name,
                'pos_session_id': order.session_id.id if order.session_id else False,
                'pos_config_id': order.config_id.id if order.config_id else False,
                'product_id': item['product_id'],
                'qty_deleted': item['qty_deleted'],
                'price_unit': item.get('price_unit', 0),
                'user_id': item['user_id'],
                'deletion_reason': item['deletion_reason'],
                'deletion_datetime': item.get('deletion_datetime', fields.Datetime.now()),
                'company_id': order.company_id.id,
            }

            # Agregar mesa si existe (restaurante)
            if 'table_id' in item and item['table_id']:
                vals['table_id'] = item['table_id']

            # Crear el registro
            record_id = audit_model.create_deletion_record(vals)
            created_ids.append(record_id)

        return created_ids


class PosOrderLine(models.Model):
    """
    Extensión del modelo pos.order.line.

    No se requieren modificaciones específicas en este modelo,
    pero se mantiene por si en el futuro se necesita agregar funcionalidad.
    """
    _inherit = 'pos.order.line'

    # Se puede agregar un campo para marcar líneas que fueron parcialmente eliminadas
    # o cualquier otra información relevante
    pass
