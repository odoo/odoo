from odoo import models, fields, tools


class EvaluacionResumen(models.Model):
    _name = "evaluacion.resumen"
    _auto = False
    _description = "Evaluacion de pesonal resumen"

    nombre = fields.Char(required=True)

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("publicado", "Publicado"),
            ("finalizado", "Finalizado"),
        ],
        default="borrador",
        required=True,
    )

    usuario_id = fields.Many2one("res.users", string="Usuario")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, "evaluacion_resumen")
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW evaluacion_resumen AS (
                SELECT
                    ROW_NUMBER() OVER() as id,
                    e.nombre,
                    e.estado,
                    u.id as usuario_id
                FROM evaluacion e
                JOIN usuario_evaluacion_rel uer ON e.id = uer.evaluacion_id
                JOIN res_users u ON uer.usuario_id = u.id
                )
            """
        )
 
