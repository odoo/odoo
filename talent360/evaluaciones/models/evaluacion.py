from odoo import api, models, fields


class Evaluacion(models.Model):
    """
    Modelo para representar una evaluación de personal en Odoo.

    :param _name (str): Nombre del modelo en Odoo.
    :param _description (str): Descripción del modelo en Odoo.
    :param nombre (fields.Char): Nombre de la evaluación. Es un campo obligatorio.
    :param estado (fields.Selection): Estado de la evaluación con opciones 'borrador', 'publicado' y 'finalizado'. Por defecto, es 'borrador'.
    :param pregunta_ids (fields.Many2many): Relación de muchos a muchos con el modelo 'pregunta' para almacenar las preguntas asociadas a la evaluación.
    :param competencia_ids (fields.Many2many): Relación de muchos a muchos con el modelo 'competencia' para almacenar las competencias asociadas a la evaluación.
    :param usuario_ids (fields.Many2many): Relación de muchos a muchos con el modelo 'res.users' para asignar usuarios a la evaluación.
    """

    _name = "evaluacion"
    _description = "Evaluacion de pesonal"
    _inherit = ["mail.thread"]

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



    def write(self, vals):
        """
        Actualiza registros de la evaluación y maneja notificaciones relacionadas con los usuarios asignados.

        Este método extiende el comportamiento estándar de 'write' para agregar funcionalidad de notificación cuando se modifican los usuarios asignados. 
        En caso de que se añada un usuario, se emite una notificación a través del sistema de mensajería.

        :return: bool: True si la actualización fue exitosa, False en caso contrario.
            
        """
        res = super(Evaluacion, self).write(vals)
        if "usuario_ids" in vals:
            for user_change in vals["usuario_ids"]:
                action, user_id = user_change
                user = self.env["res.users"].browse(user_id)
                partner_id = user.partner_id.id
                if action == 4:
                    print(f"Se ha asignado la evaluación {self.nombre} a {partner_id}")
                    self.message_post(
                        body=f"Se te ha asignado la evaluación {self.nombre}",
                        partner_ids=[partner_id],
                    )
        return res
    
    def copiar_preguntas_de_template_nom035(self):
        """
        Copia preguntas de un template de evaluación predeterminado a una nueva evaluación.

        Este método verifica si el objeto actual está vacío (self). Si lo está, crea una nueva
        evaluación con un nombre predeterminado y asigna este nuevo objeto a self. Luego, limpia
        las preguntas existentes y copia todas las preguntas de un template con ID predefinido 
       (en este caso, 331) al objeto evaluación actual.
       
       :return: object: Retorna el objeto evaluación actualizado con las preguntas copiadas del template.
        """
        
        if not self:
            new_evaluation = self.env['evaluacion'].create({
                'nombre': 'Escribe el nombre de tu evaluación',
            })
            self = new_evaluation

        self.pregunta_ids = [(5,)]

        template_id_hardcoded = 4 #CAMBIAR ID A 331

        if template_id_hardcoded:
            template = self.env['template'].browse(template_id_hardcoded)
            if template:
                pregunta_ids = template.pregunta_ids.ids
                print("IDs de preguntas:", pregunta_ids)
                self.pregunta_ids = [(6, 0, pregunta_ids)]

        return self

    def action_nom035(self):
        """
        Ejecuta la acción de copiar preguntas de un template a la evaluación actual y devuelve
        un diccionario con los parámetros necesarios para abrir una ventana de acción en Odoo.

        Este método utiliza `copiar_preguntas_de_template_nom035` para asegurarse de que la evaluación
        actual tenga las preguntas correctas, y luego configura y devuelve un diccionario con
        los detalles para abrir esta evaluación en una vista de formulario específica.

        :return: Un diccionario que contiene todos los parámetros necesarios para abrir la
        evaluación en una vista de formulario específica de Odoo.
        
        """
        self = self.copiar_preguntas_de_template_nom035()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Nombre de tu evaluación',
            'res_model': 'evaluacion',
            'view_mode': 'form',
            'view_id': self.env.ref('evaluaciones.nom035_form').id,
            'target': 'current',
            'res_id': self.id,
        }