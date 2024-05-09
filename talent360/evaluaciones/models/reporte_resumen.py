from odoo import api, models, fields


class ReporteResumen(models.Model):

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



    @api.depends("usuario_ids")
    def _compute_conteo_asignados(self):
        for record in self:
            conteo = len(record.usuario_ids)
            if conteo == 0:
                record.conteo_asignados = "Sin asignados"
            elif conteo == 1:
                record.conteo_asignados = "1 asignado"
            else:
                record.conteo_asignados = f"{conteo} asignados"

    @api.depends("usuario_ids")
    def _compute_porcentaje_respuestas(self):
        for record in self:
            conteo = len(record.usuario_ids)
            if conteo == 0:
                record.porcentaje_respuestas = 0
            else:
                respondidas = self.env["usuario.evaluacion.rel"].search(
                    [("evaluacion_id", "=", record.id), ("contestada", "=", "contestada")]
                )
                record.porcentaje_respuestas = (len(respondidas) / conteo)
