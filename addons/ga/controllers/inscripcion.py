from odoo import http
from odoo.http import request
import json

class InscripcionController(http.Controller):

    @http.route('/ga/create-inscripcion',csrf=False,  type='http', auth='public', website=True, methods=['POST'])
    def create_inscripcion(self, **post):
        body = request.httprequest.data
        data = json.loads(body)
        nombre = data.get('nombre')
        print(data)
        return json.dumps({'status': 'success', 'message': 'Inscripción creada correctamente'})
    
    @http.route('/ga/alumnos',csrf=False,  type='http', auth='public', website=True, methods=['GET'])
    def get_Alumnos(self, **post):
        inscripciones = request.env['ga.apoderado'].sudo().search([])
        inscripciones_data = [{
            'nombre': inscripcion.nombre,
        } for inscripcion in inscripciones]
        return json.dumps(inscripciones_data)
    
    
    # Metodo para obtener las notas de las diferentes materias de un estudiante
    @http.route('/ga/alumnos/notas-materia/<codigo>',csrf=False,  type='http', auth='public', website=True, methods=['GET'])
    def get_notas_materias(self,codigo):
         # Llama al método para obtener las calificaciones por materias del modelo RegistroAcademico
        calificaciones = request.env['ga.registro.academico'].obtener_calificaciones_por_materias(codigo)

        return json.dumps(calificaciones)