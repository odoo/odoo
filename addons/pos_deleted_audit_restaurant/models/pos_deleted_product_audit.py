# -*- coding: utf-8 -*-
# Copyright Jbnegoc SPA (https://jbnegoc.com)

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class PosDeletedProductAudit(models.Model):
    _name = 'pos.deleted.product.audit'
    _description = 'Productos Eliminados en POS'
    _order = 'deletion_datetime desc, id desc'

    order_name = fields.Char(string='Número de Pedido', required=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    removed_qty = fields.Float(string='Cantidad Eliminada', required=True)
    user_id = fields.Many2one('res.users', string='Usuario', required=True)
    deletion_datetime = fields.Datetime(
        string='Fecha de Eliminación',
        default=fields.Datetime.now,
        required=True,
    )
    justification = fields.Text(string='Justificación', required=True)
    justification_summary = fields.Char(
        string='Resumen Justificación',
        compute='_compute_justification_summary',
        store=True,
    )

    @api.depends('justification')
    def _compute_justification_summary(self):
        for record in self:
            justification = (record.justification or '').strip()
            record.justification_summary = justification[:80]

    @api.model
    def create_from_ui(self, values):
        user = self.env.user
        values = dict(values or {})
        values.setdefault('user_id', user.id)
        record = self.sudo().create(values)
        return record.id

    def unlink(self):
        if not self.env.user.pos_deleted_audit_can_delete:
            raise AccessError(
                _('No tiene permisos para eliminar registros de auditoría del POS.')
            )
        return super().unlink()
