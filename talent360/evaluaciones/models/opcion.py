from odoo import models, fields, api


class Opcion(models.Model):
    """
    Modelo para representar una opción para una pregunta.

    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param pregunta_id (int): Identificador de la pregunta
    :param opcion_texto (str): Texto de la opción
    :param valor (int): Valor de la opción
    """

    _name = "opcion"
    _description = "Opcion para una pregunta"

    pregunta_id = fields.Many2one("pregunta", string="Pregunta")
    opcion_texto = fields.Char("Opción", required=True)
    valor = fields.Integer(required=True, default=0)

    @api.model
    def crear_opcion_action(self, *args, **kwargs):
        """
        Método para crear una opción para las preguntas.

        :param opcion_texto (str): Texto de la opción.
        :param valor (int): Valor de la opción.

        :return: True si la opción fue creada exitosamente.
        """

        # Verifica si opcion_texto está en el contexto
        opcion_texto = self.env.context.get("default_opcion_texto")
        valor = self.env.context.get("default_valor")

        if not opcion_texto:
            raise ValueError("El campo 'Opción' es obligatorio.")

        pregunta_id = self.env.context.get("pregunta_id")
        if not pregunta_id:
            raise ValueError("Pregunta ID no proporcionado.")
        
        evaluacion_id = self.env.context.get("evaluacion_id")
        print("OOOOOOOOOOOOOOOOOOOOOOOOO")
        print(evaluacion_id)

        opcion = self.create({
            "opcion_texto": opcion_texto,
            "valor": valor,
            "pregunta_id": pregunta_id,
        })

        return {
            "name": "Agregar pregunta",
            "type": "ir.actions.act_window",
            "res_model": "pregunta",
            "view_mode": "form",
            'res_id': pregunta_id,
            "view_id": self.env.ref("evaluaciones.pregunta_view_form").id,
            "target": "new",
            "context": {
                "default_evaluacion_id": evaluacion_id,
            }
        }