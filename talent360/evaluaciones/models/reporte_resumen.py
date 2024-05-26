from odoo import api, models, fields


class ReporteResumen(models.Model):
    """
    Modelo para representar el reporte resumen de una evaluación

    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param conteo_asignados (str): Conteo de usuarios asignados a la evaluación
    :param porcentaje_respuestas (float): Porcentaje de respuestas de los usuarios asignados
    """

    _name = "evaluacion"
    _description = "Reporte Resumen"
    _inherit = "evaluacion"

    conteo_asignados = fields.Char(
        string="Asignados", compute="_compute_conteo_asignados", store="False"
    )

    porcentaje_respuestas = fields.Float(
        string="Avance",
        compute="_compute_porcentaje_respuestas",
        store="False",
    )

    @api.depends("usuario_ids", "usuario_externo_ids")
    def _compute_conteo_asignados(self):
        """
        Función que calcula el número de usuarios asignados a una evaluación
        """
        for record in self:
            if not isinstance(record.id, int):
                record.conteo_asignados = 0
                continue

            conteo = len(record.usuario_ids) + len(record.usuario_externo_ids)
            if conteo == 0:
                record.conteo_asignados = "Sin asignados"
            elif conteo == 1:
                record.conteo_asignados = "1 asignado"
            else:
                record.conteo_asignados = f"{conteo} asignados"

    @api.depends("usuario_ids", "usuario_externo_ids")
    def _compute_porcentaje_respuestas(self):
        """
        Esta función calcula el porcentaje de respuestas de los usuarios registradosy usuarios externos asignados a una evaluación.
        """

        for record in self:
            if not isinstance(record.id, int):
                record.porcentaje_respuestas = 0
                continue

            conteo = len(record.usuario_ids) + len(record.usuario_externo_ids)
            if conteo == 0:
                record.porcentaje_respuestas = 0
            else:
                respondidas = self.env["usuario.evaluacion.rel"].search(
                    [
                        ("evaluacion_id.id", "=", record.id),
                        ("contestada", "=", "contestada"),
                    ]
                )
                record.porcentaje_respuestas = len(respondidas) / conteo
