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
        """
        Copia preguntas de un template de evaluación predeterminado a una nueva evaluación.

        Este método verifica si el objeto actual está vacío (self). Si lo está, crea una nueva
        evaluación con un nombre predeterminado y asigna este nuevo objeto a self. Luego, limpia
        las preguntas existentes y copia todas las preguntas de un template con ID predefinido 
        (en este caso, 332) al objeto evaluación actual.

        Returns:
        object: Retorna el objeto evaluación actualizado con las preguntas copiadas del template.
        """

        if not self:
            new_evaluation = self.env['evaluacion'].create({
                'nombre': 'Evaluacion Clima',
            })
            self = new_evaluation

        self.pregunta_ids = [(5,)]

        template_id_hardcoded = 332

        if template_id_hardcoded:
            template = self.env['template'].browse(template_id_hardcoded)
            if template:
                pregunta_ids = template.pregunta_ids.ids
                print("IDs de preguntas:", pregunta_ids)
                self.pregunta_ids = [(6, 0, pregunta_ids)]

        return self

    def action_clima(self):
        """
        Ejecuta la acción de copiar preguntas de un template a la evaluación actual y devuelve
        un diccionario con los parámetros necesarios para abrir una ventana de acción en Odoo.

        Este método utiliza `copiar_preguntas_de_template_nom035` para asegurarse de que la evaluación
        actual tenga las preguntas correctas, y luego configura y devuelve un diccionario con
        los detalles para abrir esta evaluación en una vista de formulario específica.

        Returns:
        dict: Un diccionario que contiene todos los parámetros necesarios para abrir la
        evaluación en una vista de formulario específica de Odoo.
        
        """

        self = self.copiar_preguntas_de_template()

        # Retornar la acción con la vista como destino
        return {
            'type': 'ir.actions.act_window',
            'name': 'Evaluación Clima',
            'res_model': 'evaluacion',
            'view_mode': 'form',
            'view_id': self.env.ref('evaluaciones.clima_form').id,
            'target': 'current',
            'res_id': self.id,
        }

    def action_redirect_to_evaluacion(self):
        """
        Ejecuta la acción de redireccionar a la lista de evaluaciones y devuelve un diccionario

        Este método utiliza los parámetros necesarios para redireccionar a la lista de evaluaciones

        Returns:
        dict: Un diccionario que contiene todos los parámetros necesarios para redireccionar la
        a una vista de la lista de las evaluaciones.
        
        """

        return {
            'name': 'Evaluación',
            'type': 'ir.actions.act_window',
            'res_model': 'evaluacion',
            'view_mode': 'tree,form',
            'target': 'current',
        }