from odoo import models, fields

class UsuariosExternos(models.Model):
    


    _name = "usuario.externo"
    _description = "Usuarios externos a la plataforma. Se utiliza para que puedan responer encuestas sin tener un usuario"
    _rec_name = "nombre"

    nombre = fields.Char(string="Nombre Completo", required=True)
    email = fields.Char(string="Correo electrónico", required=True)
    puesto = fields.Char()
    nivel_jerarquico = fields.Char(string="Nivel jerárquico")
    direccion = fields.Char(string="Dirección")
    gerencia = fields.Char(string="Gerencia")
    jefatura = fields.Char(string="Jefatura")
    genero = fields.Char(string="Género")
    fecha_ingreso = fields.Date(string="Fecha de ingreso")
    fecha_nacimiento = fields.Date(string="Fecha de nacimiento")
    region = fields.Char(string="Ubicación/Región")

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluación")
    

