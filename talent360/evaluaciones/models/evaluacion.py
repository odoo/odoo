from odoo import api, models, fields


class Evaluacion(models.Model):
    _name = "evaluacion"
    _description = "Evaluacion de pesonal"
    _inherit = ["mail.thread"]

    nombre = fields.Char(required=True)
    descripcion = fields.Text()
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

    template_id = fields.Many2one("template", string="Plantilla")

    # do something on new usuario assigned

    def write(self, vals):
        res = super(Evaluacion, self).write(vals)
        if "usuario_ids" in vals:
            for user_change in vals["usuario_ids"]:
                action, user_id = user_change
                user = self.env["res.users"].browse(user_id)
                partner_id = user.partner_id.id
                if action == 4:
                    print(f"Se ha asignado la evaluación {self.nombre} a {partner_id}")
                    # Send email to assigned user
                    self.message_post(
                        body=f"Se te ha asignado la evaluación {self.nombre}",
                        partner_ids=[partner_id],
                    )
        return res
    
    # Método para copiar preguntas de la plantilla a la evaluación
    def copiar_preguntas_de_template(self):
        if not self:
            new_evaluation = self.env['evaluacion'].create({
                'nombre': 'Evaluacion Clima',
            })
            self = new_evaluation

        self.pregunta_ids = [(5,)]

        template_id_hardcoded = 5

        if template_id_hardcoded:
            template = self.env['template'].browse(template_id_hardcoded)
            if template:
                pregunta_ids = template.pregunta_ids.ids
                print("IDs de preguntas:", pregunta_ids)
                self.pregunta_ids = [(6, 0, pregunta_ids)]

    @api.model
    def action_clima(self):
        self.copiar_preguntas_de_template()
        view = self.env['ir.ui.view'].search([('name', '=', 'Evaluaciones.clima_form')])
        view_id = view.id

        print(view_id)

        return {
            'name': 'Clima',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'evaluacion',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

            
    # Actualiza las preguntas cuando se selecciona una plantilla
    # @api.onchange('template_id')
    # def onchange_template_id(self):
    #     self.copiar_preguntas_de_template()
