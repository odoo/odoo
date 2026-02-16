# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmRelationshipType(models.Model):
    _name = "crm.relationship.type"
    _description = "CRM Relationship Type"
    _order = "sequence, name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(string="Codigo", required=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    active = fields.Boolean(string="Activo", default=True)

    _sql_constraints = [
        ("crm_relationship_type_code_unique", "unique(code)", "El codigo debe ser unico."),
    ]
