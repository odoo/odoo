from odoo import models, fields

class Categoria(models.Model):
    """
    Modelo para representar una categoría de pregunta.

    :param _name (str): Nombre del modelo en Odoo.
    :param _description (str): Descripción del modelo en Odoo.
    :param nombre (fields.Char): Nombre de la categoría. Es un campo obligatorio.
    :param descripcion (fields.Text): Descripción de la categoría.
    :param pregunta_ids (fields.One2many): Relación uno a muchos con el modelo 'pregunta' para las preguntas asociadas.
    """

    _name = "categoria"
    _description = "Categoría para preguntas"

    nombre = fields.Char("Nombre", required=True)
    pregunta_ids = fields.One2many("pregunta", "categoria_id", string="Preguntas")

    def name_get(self):
        """
        Sobrescribe el método name_get para mostrar el campo 'nombre' como
        la representación de las categorías en los campos Many2one.
        """
        result = []
        for record in self:
            result.append((record.id, record.nombre))
        return result
