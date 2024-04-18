from odoo import models, fields, api


class Evaluacion(models.Model):
    _name = "evaluacion"
    _description = "Evaluacion de pesonal"
    # _inherit = ["mail.thread"]

    nombre = fields.Char(required=True)

    @api.model
    def _get_evaluation_type(self):
        if self.env.context.get("default_tipo") == "NOM_035":
            return [("NOM_035", "NOM-035")]
        elif self.env.context.get("default_tipo") == "CLIMA":
            return [("CLIMA", "Clima Laboral")]
        else:
            return [("90", "90 Grados"), ("180", "180 Grados"), ("270", "270 Grados"), ("360", "360 Grados")]

    def get_evaluation_default_type(self):
        return self._get_evaluation_type(self)[0][0]

    tipo = fields.Selection(selection=_get_evaluation_type,
                            required=True, default="get_evaluation_default_type")

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("publicado", "Publicado"),
            ("finalizado", "Finalizado"),
        ],
        default="borrador",
        required=True,
    )

    pregunta_ids = fields.Many2many(
        "pregunta",
        "pregunta_evaluacion_rel",
        "evaluacion_id",
        "pregunta_id",
        string="Preguntas",
    )

    competencia_ids = fields.Many2many(
        "competencia",
        "competencia_evaluacion_rel",
        "evaluacion_id",
        "competencia_id",
        string="Competencias",
    )

    usuario_ids = fields.Many2many(
        "res.users",
        "usuario_evaluacion_rel",
        "evaluacion_id",
        "usuario_id",
        string="Asignados",
    )

    @api.onchange('competencia_ids')
    def _onchange_competencia_ids(self):
        if self.competencia_ids:
            competencia_preguntas = self.competencia_ids.mapped('pregunta_ids')
            self.pregunta_ids = competencia_preguntas
        else:
            self.pregunta_ids = False
    # # do something on new usuario assigned

    # def write(self, vals):
    #     res = super(Evaluacion, self).write(vals)
    #     if "usuario_ids" in vals:
    #         for user_change in vals["usuario_ids"]:
    #             action, user_id = user_change
    #             user = self.env["res.users"].browse(user_id)
    #             partner_id = user.partner_id.id
    #             if action == 4:
    #                 print(
    #                     f"Se ha asignado la evaluación {self.nombre} a {partner_id}")
    #                 # Send email to assigned user
    #                 self.message_post(
    #                     body=f"Se te ha asignado la evaluación {self.nombre}",
    #                     partner_ids=[partner_id],
    #                 )
    #     return res
