from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date

class Objetivo(models.Model):
    _name = "objetivo"
    _description = "Objetivos de desempeño"

    titulo = fields.Char(required=True, string="Título")
    descripcion = fields.Text(required=True, string="Descripción", help="Descripción del objetivo")
    metrica = fields.Selection(
        [
            ("porcentaje", "Porcentaje"),
            ("monto", "Monto"),
        ],
        default="porcentaje",
        required=True,
        string="Métrica",
        help="¿Cómo se medirá el objetivo? Ej. Porcentaje o Monto",
    )

    tipo = fields.Selection(
        [
            ("puesto", "Del puesto"),
            ("estrategico", "Estratégico"),
        ],
        default="puesto",
        required=True,
        help="Tipo de objetivo",
    )

    orden = fields.Selection(
        [
            ("ascendente", "Ascendente"),
            ("descendente", "Descendente"),
        ],
        default="ascendente",
        required=True,
        help="Si el objetivo es para lograr una meta, es ascendente, si es para reducir algo, es descendente",
    )

    peso = fields.Integer(required=True, help="Peso del objetivo en la evaluación")
    piso_minimo = fields.Integer(required=True, string="Piso Mínimo", help="¿Cuál es el mínimo aceptable?")
    piso_maximo = fields.Integer(required=True, string="Piso Máximo", help="¿Cuál es el máximo aceptable?")
    fecha_fin = fields.Date(required=True, string="Fecha final", default=fields.Datetime.today() ,help="Fecha en la que se debe cumplir el objetivo")
    resultado = fields.Integer(store=True)
    estado = fields.Selection(
        [
            ("rojo", "No cumple con las expectativas"),
            ("amarillo", "Medianamente cumple con las expectativas"),
            ("verde", "Cumple con las expectativas"),
            ("azul", "Supera las expectativas")
        ],
        default="rojo",
        compute="_compute_estado",
        store=True,
    )

    usuario_ids = fields.Many2many(
        "res.users",
        "usuario_objetivo_rel",
        "objetivo_id",
        "usuario_id",
        string="Asignados",
    )
    
    evaluador = fields.Char()

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
    
    @api.constrains("fecha_fin")
    def _check_fecha_fin(self):
        for record in self:
            if record.fecha_fin and record.fecha_fin < date.today():
                raise ValidationError("La fecha final debe ser mayor a la fecha de hoy")
            
    @api.depends("resultado", "piso_maximo")
    def _compute_estado(self):
        for record in self:
            if record.piso_maximo and record.piso_minimo and record.resultado and record.orden:
                if record.orden == "descendente": 
                    ratio = (record.piso_minimo - record.resultado) / (record.piso_minimo - record.piso_maximo)
                    
                if record.orden == "ascendente":
                    ratio = 1 - (record.piso_maximo - record.resultado) / (record.piso_maximo - record.piso_minimo)
                    
                if record.orden == "ascendente":
                    if 0 <= ratio <= 0.6:
                        record.estado = "rojo"
                    elif 0.61 <= ratio <= 0.85:
                        record.estado = "amarillo"
                    elif 0.851 <= ratio <= 1:
                        record.estado = "verde"
                    elif ratio > 1:
                        record.estado = "azul"
            