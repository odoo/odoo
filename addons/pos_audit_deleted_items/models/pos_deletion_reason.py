# -*- coding: utf-8 -*-
# © 2026 Jbnegoc SPA - Todos los derechos reservados
# Desarrollado por: Jbnegoc SPA

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosDeletionReason(models.Model):
    """
    Modelo para almacenar justificaciones predeterminadas de eliminación.

    Este modelo permite a los administradores configurar razones
    comunes de eliminación que se mostrarán en el popup del POS
    para agilizar el ingreso de datos.

    Ubicación en menú: Punto de Ventas / Configuración / Justificaciones de Eliminaciones
    """
    _name = 'pos.deletion.reason'
    _description = 'Justificaciones de Eliminación POS'
    _order = 'sequence, name'

    name = fields.Char(
        string='Justificación',
        required=True,
        translate=True,
        help='Texto de la justificación que aparecerá en el POS'
    )

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden en que aparecerá en el listado del POS. '
             'Menor número = mayor prioridad.'
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está inactivo, no aparecerá en el POS'
    )

    description = fields.Text(
        string='Descripción',
        help='Descripción interna de cuándo usar esta justificación'
    )

    @api.constrains('name')
    def _check_name(self):
        """
        Valida que el nombre de la justificación no esté vacío
        y tenga al menos 3 caracteres.
        """
        for record in self:
            if record.name and len(record.name.strip()) < 3:
                raise ValidationError(
                    _('La justificación debe tener al menos 3 caracteres.')
                )

    def name_get(self):
        """
        Personaliza el nombre mostrado en listas desplegables.
        """
        result = []
        for record in self:
            name = record.name
            if len(name) > 50:
                name = name[:50] + '...'
            result.append((record.id, name))
        return result
