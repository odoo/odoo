from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import date


class Objetivo(models.Model):
    """
    Modelo para representar un objetivo de desempeño en Odoo

    :param _name(str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param titulo (fields.Char): Título del objetivo
    :param descripcion (fields.Text): Descrpición del objetivo
    :param metrica(fields.Selection): Seleccionar la forma en la que se va a medir el objetivo
    :param tipo(fields.Selection): Seleccionar el tipo del objetivo
    :param orden(fields.Selection): Seleccionar si el objetivo es para incrementar o decrementar un comportamiento
    :param peso(fields.Integer): Peso del objetivo de la evaluación
    :param piso_minimo(fields.Integer): El resultado mínimo que se espera
    :param piso_maximo(fields.Integer): El resultado máximo que se espera
    :param fecha_fin(fields.Date): Fecha final del objetivo
    :param resultado(fields.Integer): Resultado del objetivo
    :param estado(fields.Selection): Seleccionar el estado actual del objetivo
    :param usuario_ids(fields.Many2Many): Arreglo de usuarios asignado a un objetivo
    :param evaluador(fields.Char): Nombre del evaluador del objetivo
    """

    _name = "objetivo"
    _description = "Objetivos de desempeño"
    _rec_name = "titulo"

    titulo = fields.Char(required=True, string="Título")
    descripcion = fields.Text(
        required=True, string="Descripción", help="Descripción del objetivo"
    )
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
    piso_minimo = fields.Integer(
        required=True, string="Piso Mínimo", help="¿Cuál es el mínimo aceptable?"
    )
    piso_maximo = fields.Integer(
        required=True, string="Piso Máximo", help="¿Cuál es el máximo aceptable?"
    )
    fecha_fin = fields.Date(
        required=True,
        string="Fecha final",
        default=fields.Datetime.today(),
        help="Fecha en la que se debe cumplir el objetivo",
    )
    resultado = fields.Integer(store=True)
    estado = fields.Selection(
        [
            ("rojo", "No cumple con las expectativas"),
            ("amarillo", "Medianamente cumple con las expectativas"),
            ("verde", "Cumple con las expectativas"),
            ("azul", "Supera las expectativas"),
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
    def _checar_pisos(self):
        """
        Método para verificar que el piso mínimo sea menor al piso máximo en todo momento. Asimismo, se verifica que los valores de piso mínimo y piso máximo sean mayores a 0

        De no ser el caso, el sistema manda un error al usuario.
        """
        for registro in self:
            if registro.piso_minimo >= registro.piso_maximo:
                raise ValidationError(_("El piso mínimo debe ser menor al piso máximo"))
            if registro.piso_minimo < 0 or registro.piso_maximo < 0:
                raise ValidationError(
                    _("Los pisos minimos y maximos deben ser mayores a 0")
                )

    @api.constrains("peso")
    def _checar_peso(self):
        """
        Método para verificar que el valor del peso sea entre 1 y 100.

        De no ser el caso, el sistema manda un error al usuario.
        """
        for registro in self:
            if registro.peso > 100 or registro.peso <= 0:
                raise ValidationError(_("El peso debe estar en el rango de 1 y 100"))

    def write(self, vals):
        """
        Método funcional cuando se edita un objetivo.

        Método para verificar que el piso mínimo sea menor al piso máximo. También, se verifica que los valores de piso mínimo y piso máximo sean mayores a 0.

        Método para verificar que el valor del peso sea entre 1 y 100.

        De no ser ningún caso, el sistema manda un error al usuario.
        """
        if "piso_minimo" in vals or "piso_maximo" in vals:
            nuevo_piso_minimo = vals.get("piso_minimo", self.piso_minimo)
            nuevo_piso_maximo = vals.get("piso_maximo", self.piso_maximo)
            if nuevo_piso_minimo >= nuevo_piso_maximo:
                raise ValidationError(_("El piso mínimo debe ser menor al piso máximo"))
            if nuevo_piso_minimo < 0 or nuevo_piso_maximo < 0:
                raise ValidationError(
                    _("Los pisos mínimos y máximos deben ser mayores a 0")
                )

        if "peso" in vals:
            nuevo_peso = vals.get("peso", self.peso)
            if nuevo_peso > 100 or nuevo_peso <= 0:
                raise ValidationError(_("El peso debe estar en el rango de 1 y 100"))
        return super(Objetivo, self).write(vals)

    @api.constrains("fecha_fin")
    def _checar_fecha_fin(self):
        """
        Método para verificar que la fecha final sea mayor a la fecha de hoy.

        De no ser el caso, el sistema manda un error al usuario.
        """
        for registro in self:
            if registro.fecha_fin and registro.fecha_fin < date.today():
                raise ValidationError(
                    _("La fecha final debe ser mayor a la fecha de hoy")
                )

    @api.depends("resultado", "piso_maximo")
    def _compute_estado(self):
        """
        Método que calcula el estado actual del objetivo dependiendo del resultado
        """
        for registro in self:
            if registro.piso_maximo and registro.resultado:
                ratio = registro.resultado / registro.piso_maximo
                if 0 <= ratio <= 0.6:
                    registro.estado = "rojo"
                elif 0.61 <= ratio <= 0.85:
                    registro.estado = "amarillo"
                elif 0.851 <= ratio <= 1:
                    registro.estado = "verde"
                elif ratio > 1:
                    registro.estado = "azul"

    @api.constrains("usuario_ids")
    def _checar_usuario_ids(self):
        """
        Método para verificar que el número de usuarios asignados a un objetivo sea mayor a 0.

        De no ser el caso, el sistema manda un error al usuario.
        """
        for registro in self:
            if not registro.usuario_ids:
                raise ValidationError(_("Debe asignar al menos un usuario al objetivo"))
