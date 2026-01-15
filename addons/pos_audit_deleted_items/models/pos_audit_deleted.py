# -*- coding: utf-8 -*-
# © 2026 Jbnegoc SPA - Todos los derechos reservados
# Desarrollado por: Jbnegoc SPA

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosAuditDeleted(models.Model):
    """
    Modelo principal para almacenar registros de auditoría de productos eliminados.

    Cada vez que un usuario elimina una cantidad o línea de producto en el POS,
    se crea un registro en este modelo con toda la información de trazabilidad.

    Ubicación en menú: Punto de Ventas / Reportes / Productos Eliminados
    """
    _name = 'pos.audit.deleted'
    _description = 'Auditoría de Productos Eliminados en POS'
    _order = 'deletion_datetime desc'
    _rec_name = 'display_name'

    # Campo computado para el nombre del registro
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True
    )

    # Información del pedido desde donde se eliminó
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Pedido POS',
        ondelete='cascade',
        help='Referencia al pedido desde donde se eliminó el producto'
    )

    pos_order_name = fields.Char(
        string='Número de Pedido',
        required=True,
        help='Número de referencia del pedido en el POS'
    )

    pos_session_id = fields.Many2one(
        'pos.session',
        string='Sesión POS',
        ondelete='set null',
        help='Sesión del POS donde ocurrió la eliminación'
    )

    # Información del producto eliminado
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='restrict',
        help='Producto que fue eliminado'
    )

    product_name = fields.Char(
        string='Nombre del Producto',
        required=True,
        help='Nombre del producto al momento de la eliminación'
    )

    product_code = fields.Char(
        string='Referencia Interna',
        help='Código de referencia interna del producto'
    )

    # Cantidad eliminada
    qty_deleted = fields.Float(
        string='Cantidad Eliminada',
        required=True,
        help='Cantidad de unidades eliminadas'
    )

    # Precio unitario y total
    price_unit = fields.Float(
        string='Precio Unitario',
        help='Precio unitario del producto al momento de la eliminación'
    )

    price_subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_price_subtotal',
        store=True,
        help='Subtotal de la línea eliminada (cantidad × precio)'
    )

    # Información del usuario que eliminó
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
        help='Usuario que realizó la eliminación'
    )

    user_name = fields.Char(
        string='Nombre del Usuario',
        required=True,
        help='Nombre del usuario al momento de la eliminación'
    )

    # Fecha y hora de la eliminación
    deletion_datetime = fields.Datetime(
        string='Fecha y Hora de Eliminación',
        required=True,
        default=fields.Datetime.now,
        help='Fecha y hora exacta en que se eliminó el producto'
    )

    # Justificación de la eliminación
    deletion_reason = fields.Text(
        string='Justificación de la Eliminación',
        required=True,
        help='Razón por la cual se eliminó el producto'
    )

    deletion_reason_summary = fields.Char(
        string='Resumen Justificación',
        compute='_compute_deletion_reason_summary',
        store=True,
        help='Resumen corto de la justificación para vista de lista'
    )

    # Información adicional del POS Config
    pos_config_id = fields.Many2one(
        'pos.config',
        string='Punto de Venta',
        ondelete='restrict',
        help='Configuración del punto de venta donde ocurrió'
    )

    # Información de mesa (si es restaurante)
    table_id = fields.Many2one(
        'restaurant.table',
        string='Mesa',
        ondelete='set null',
        help='Mesa del restaurante (si aplica)'
    )

    # Campos técnicos
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        help='Compañía a la que pertenece el registro'
    )

    @api.depends('product_name', 'pos_order_name', 'deletion_datetime')
    def _compute_display_name(self):
        """
        Computa el nombre de visualización del registro.
        Formato: "Producto - Pedido - Fecha"
        """
        for record in self:
            if record.deletion_datetime:
                date_str = fields.Datetime.to_string(record.deletion_datetime)[:16]
            else:
                date_str = ''
            record.display_name = f"{record.product_name} - {record.pos_order_name} - {date_str}"

    @api.depends('qty_deleted', 'price_unit')
    def _compute_price_subtotal(self):
        """
        Computa el subtotal de la línea eliminada.
        """
        for record in self:
            record.price_subtotal = record.qty_deleted * record.price_unit

    @api.depends('deletion_reason')
    def _compute_deletion_reason_summary(self):
        """
        Computa un resumen corto de la justificación para mostrar en lista.
        Toma las primeras 50 caracteres.
        """
        for record in self:
            if record.deletion_reason:
                summary = record.deletion_reason.strip()
                if len(summary) > 50:
                    summary = summary[:50] + '...'
                record.deletion_reason_summary = summary
            else:
                record.deletion_reason_summary = ''

    @api.model
    def create_deletion_record(self, vals):
        """
        Método para crear un registro de eliminación desde el frontend del POS.

        :param vals: dict con los valores del registro
        :return: ID del registro creado
        """
        # Validar que se proporcionen los campos mínimos requeridos
        required_fields = ['pos_order_name', 'product_id', 'qty_deleted',
                          'user_id', 'deletion_reason']
        missing_fields = [f for f in required_fields if f not in vals]
        if missing_fields:
            raise UserError(
                _('Faltan campos requeridos: %s') % ', '.join(missing_fields)
            )

        # Obtener información del producto
        product = self.env['product.product'].browse(vals['product_id'])
        vals['product_name'] = product.display_name
        vals['product_code'] = product.default_code or ''

        # Obtener información del usuario
        user = self.env['res.users'].browse(vals['user_id'])
        vals['user_name'] = user.name

        # Obtener precio unitario si no se proporcionó
        if 'price_unit' not in vals:
            vals['price_unit'] = product.lst_price

        # Crear el registro
        record = self.create(vals)
        return record.id

    def unlink(self):
        """
        Sobrescribe el método unlink para controlar quién puede eliminar registros.
        Solo usuarios con el permiso 'pos_audit_can_delete' pueden eliminar.
        """
        # Verificar si el usuario actual tiene permiso para eliminar
        if not self.env.user.pos_audit_can_delete:
            raise UserError(
                _('No tiene permisos para eliminar registros de auditoría. '
                  'Contacte a su supervisor o gerente.')
            )
        return super(PosAuditDeleted, self).unlink()

    def action_view_order(self):
        """
        Acción para ver el pedido relacionado desde el registro de auditoría.
        """
        self.ensure_one()
        if not self.pos_order_id:
            raise UserError(_('No hay pedido asociado a este registro.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedido POS'),
            'res_model': 'pos.order',
            'res_id': self.pos_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_product(self):
        """
        Acción para ver el producto relacionado desde el registro de auditoría.
        """
        self.ensure_one()
        if not self.product_id:
            raise UserError(_('No hay producto asociado a este registro.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Producto'),
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
