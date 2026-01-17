# -*- coding: utf-8 -*-
# Copyright Jbnegoc SPA (https://jbnegoc.com)

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_delete_justification_enabled = fields.Boolean(
        string='Solicitar justificación al eliminar en POS',
        help='Si está activo, el POS solicitará una justificación al eliminar '
             'cantidades o líneas de productos.'
    )
    pos_deleted_audit_can_delete = fields.Boolean(
        string='Acceso y eliminación de auditorías POS',
        compute='_compute_pos_deleted_audit_can_delete',
        inverse='_inverse_pos_deleted_audit_can_delete',
        help='Permite acceder al reporte de productos eliminados y borrar registros.'
    )

    def _compute_pos_deleted_audit_can_delete(self):
        group = self.env.ref(
            'pos_deleted_audit_restaurant.group_pos_deleted_audit_manager',
            raise_if_not_found=False,
        )
        for user in self:
            user.pos_deleted_audit_can_delete = bool(group in user.groups_id) if group else False

    def _inverse_pos_deleted_audit_can_delete(self):
        group = self.env.ref(
            'pos_deleted_audit_restaurant.group_pos_deleted_audit_manager',
            raise_if_not_found=False,
        )
        if not group:
            return
        for user in self:
            if user.pos_deleted_audit_can_delete:
                user.groups_id = [(4, group.id)]
            else:
                user.groups_id = [(3, group.id)]
