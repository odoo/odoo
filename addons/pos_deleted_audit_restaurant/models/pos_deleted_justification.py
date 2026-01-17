# -*- coding: utf-8 -*-
# Copyright Jbnegoc SPA (https://jbnegoc.com)

from odoo import fields, models


class PosDeletedJustification(models.Model):
    _name = 'pos.deleted.justification'
    _description = 'Justificaciones de Eliminaciones en POS'

    name = fields.Char(string='Justificación', required=True)
    description = fields.Text(string='Descripción')
    active = fields.Boolean(default=True)
