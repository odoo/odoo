from odoo import models, fields

class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    # ANULACIÓN DE CAMPO
    # Al redeclarar el campo 'birthday' aquí, sin el atributo 'groups',
    # esta definición toma prioridad sobre cualquier otra que exista en otro módulo.
    # Esto efectivamente elimina la restricción de seguridad que causa el error.
    birthday = fields.Date(string="Birthday")