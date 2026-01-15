# -*- coding: utf-8 -*-
# © 2026 Jbnegoc SPA - Todos los derechos reservados
# Desarrollado por: Jbnegoc SPA

from odoo import api, fields, models, _


class ResUsers(models.Model):
    """
    Extensión del modelo res.users para agregar campos de control
    de auditoría de eliminaciones en el POS.

    Se agregan dos campos booleanos en la pestaña "Permisos / Accesos":
    1. pos_audit_enabled: Activa la auditoría para este usuario
    2. pos_audit_can_delete: Permite eliminar registros de auditoría
    """
    _inherit = 'res.users'

    # Campo para habilitar la auditoría de eliminaciones para este usuario
    pos_audit_enabled = fields.Boolean(
        string='Auditar Eliminaciones en POS',
        default=False,
        help='Si está activo, todas las eliminaciones de productos '
             'en el POS realizadas por este usuario serán auditadas '
             'y se solicitará una justificación.'
    )

    # Campo para autorizar al usuario a eliminar registros de auditoría
    pos_audit_can_delete = fields.Boolean(
        string='Puede Eliminar Auditorías POS',
        default=False,
        help='Si está activo, este usuario podrá eliminar registros '
             'de auditoría de productos eliminados en el POS. '
             'Típicamente solo gerentes o supervisores deben tener '
             'este permiso.'
    )

    @api.model
    def get_pos_audit_settings(self, user_id):
        """
        Método para obtener la configuración de auditoría de un usuario.
        Utilizado por el frontend del POS para saber si debe auditar o no.

        :param user_id: ID del usuario
        :return: dict con configuración de auditoría
        """
        user = self.browse(user_id)
        return {
            'audit_enabled': user.pos_audit_enabled,
            'can_delete': user.pos_audit_can_delete,
        }
