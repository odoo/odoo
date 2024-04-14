from odoo import models, fields

class Objetivo(models.Model):
    _name = "objetivo"
    _description = "Objetivos de desempeño"

    titulo = fields.Char(required=True)
    descripcion = fields.Char(required=True)
    metrica = fields.Selection(
        [
            ("porcentaje", "Porcentaje"),
            ("monto", "Monto"),
        ],
        default="porcentaje",
        required=True,
    )

    tipo = fields.Selection(
        [
            ("puesto", "Del puesto"),
            ("estrategico", "Estratégico"),
        ],
        default="puesto",
        required=True,
    )

    orden = fields.Selection(
        [
            ("ascendente", "Ascendente"),
            ("descendente", "Descendente"),
        ],
        default="ascendente",
        required=True,
    )

    peso = fields.Integer(required=True)
    piso_minimo = fields.Integer(required=True)
    piso_maximo = fields.Integer(required=True)
    resultado = fields.Integer()

    usuario_ids = fields.Many2many(
        "res.users",
        "usuario_objetivo_rel",
        "objetivo_id",
        "usuario_id",
        string="Asignados",
    )