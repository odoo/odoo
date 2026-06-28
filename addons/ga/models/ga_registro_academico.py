from odoo import fields, models

class RegistroAcademico(models.Model):
    _name = "ga.registro.academico"
    _description = "GA Registro Academico"

    fecha_entrega = fields.Datetime()
    calificacion = fields.Float()
    alumno_id = fields.Many2one("ga.alumno",required=True)
    actividad_academica_id = fields.Many2one("ga.actividad.academica",required=True)

    def obtener_calificaciones_por_materias(self, alumno_id):
        # Realiza una consulta para obtener las calificaciones por materias para un alumno específico
        notas = self.env['ga.registro.academico'].search([
            ('alumno_id', '=', alumno_id)
        ])
        
        resultados = {}
        for nota in notas:
            materia_id = nota.actividad_academica_id.paralelo_profesor_id.plan_estudio_id.materia_id.id
            materia_nombre = nota.actividad_academica_id.paralelo_profesor_id.plan_estudio_id.materia_id.descripcion
            calificacion = nota.calificacion

            if materia_id not in resultados:
                resultados[materia_id] = {'nombre': materia_nombre, 'calificaciones': []}

            resultados[materia_id]['calificaciones'].append(calificacion)

        return resultados