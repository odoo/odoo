from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError

class Objetivo(models.Model):
    _name = "objetivo"
    _description = "Objetivos de desempeño"

    titulo = fields.Char(required=True, string="Título")
    descripcion = fields.Char(required=True, string="Descripción")
    metrica = fields.Selection(
        [
            ("porcentaje", "Porcentaje"),
            ("monto", "Monto"),
        ],
        default="porcentaje",
        required=True,
        string="Métrica",
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
    piso_minimo = fields.Integer(required=True, string="Piso Mínimo")
    piso_maximo = fields.Integer(required=True, string="Piso Máximo")
    resultado = fields.Integer()

    usuario_ids = fields.Many2many(
        "res.users",
        "usuario_objetivo_rel",
        "objetivo_id",
        "usuario_id",
        string="Asignados",
    )

    @api.constrains("piso_minimo", "piso_maximo")
    def _check_pisos(self):
        for record in self:
            if record.piso_minimo >= record.piso_maximo:
                raise ValidationError("El piso mínimo debe ser menor al piso máximo")
            if record.piso_minimo < 0 or record.piso_maximo < 0:
                raise ValidationError("Los pisos minimos y maximos deben ser mayores a 0")

    @api.constrains("peso")
    def _check_peso(self):
        for record in self:
            if record.peso > 100 or record.peso <= 0:
                raise ValidationError("El peso debe estar en el rango de 1 y 100")
            
    def write(self, vals):
        if "piso_minimo" in vals or "piso_maximo" in vals:
            new_piso_minimo = vals.get("piso_minimo", self.piso_minimo)
            new_piso_maximo = vals.get("piso_maximo", self.piso_maximo)
            if new_piso_minimo >= new_piso_maximo:
                raise ValidationError("El piso mínimo debe ser menor al piso máximo")
            if new_piso_minimo < 0 or new_piso_maximo < 0:
                raise ValidationError("Los pisos mínimos y máximos deben ser mayores a 0")
            
        if "peso" in vals:
            new_peso = vals.get("peso", self.peso)
            if new_peso > 100 or new_peso <= 0:
                raise ValidationError("El peso debe estar en el rango de 1 y 100")
        return super(Objetivo, self).write(vals)