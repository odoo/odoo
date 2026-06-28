from odoo import http
from odoo.http import request, route, Response
from datetime import datetime, timedelta
import json
from ..service import ga_notification_service as Notificacion
class GestionController(http.Controller):
    @http.route('/api/gestion', auth='public', type='http', methods=['GET'], csrf=False, website=True)
    def get_gestiones(self, **kw):
        gestiones = request.env['ga.gestion'].sudo().search([])
        gestiones_data = [{
            'codigo': gestion.codigo,
        } for gestion in gestiones]
        return json.dumps(gestiones_data)
    
class ProfesorController(http.Controller):
    @http.route('/ga/profesor/lista-curso-materias',csrf=False,  type='http', auth='public', website=True, methods=['GET'])
    def get_lista_curso_materias(self, **post):
        response_data = {}
        
        body = request.httprequest.data
        data = json.loads(body)
        codigo_profesor = data.get('codigoPersona')
        profesor = request.env['hr.employee'].sudo().search([('id', '=', codigo_profesor)])
        
        response_data["profesor"] = {}
        if len(profesor) > 0:
            paralelo_profesores = request.env['ga.paralelo.profesor'].sudo().search([('profesor_id', '=', profesor.id)])
            grados = request.env['ga.grado'].sudo().search([])
            cursos_data = []
            for grado in grados:
                if not grado.exists(): continue
                for p_profesor in paralelo_profesores:
                    if not p_profesor.exists(): continue
                    plan_estudios = request.env['ga.plan.estudio'].sudo().search(
                        [('id', '=', p_profesor.plan_estudio_id.id),('grado_id', '=', grado.id)]
                    )
                    if not plan_estudios.exists(): continue
                    materias_data = []
                    for p_estudio in plan_estudios:
                        if not p_estudio.exists(): continue
                        materia = request.env['ga.materia'].sudo().search([('id', '=', p_estudio.materia_id.id)])
                        materias_data.append({
                            'materiaId': materia.id,
                            'nombreMateria':materia.descripcion
                        })

                    nivel = request.env['ga.nivel'].sudo().search([('id', '=', grado.nivel_id.id)])
                    paralelo = request.env['ga.paralelo'].sudo().search([('id', '=', p_profesor.paralelo_id.id)])
                    
                    cursos_data.append({
                        'cursoId': grado.id,
                        'pareleloId': paralelo.id,
                        'nombreCurso': '{} {} de {}'.format(grado.descripcion, paralelo.descripcion, nivel.descripcion),
                        'materias': materias_data
                    })

            # datos del profesor
            response_data["profesor"] = {
                'id':profesor[0].id,
                'nombre':profesor[0].name,
                'cursos' : cursos_data
            }
        return json.dumps(response_data)
    
    @http.route('/ga/profesor/generar-notificacion-asistencia ',csrf=False,  type='http', auth='public', website=True, methods=['PÔST'])
    def generar_notificacion_asistencia(self, **post):
        response_data = {}
        
        body = request.httprequest.data
        data = json.loads(body)
        codigo_profesor = data.get('codigoPersona')
        materia_id = data.get('materiaId')
        grado_id = data.get('cursoId')
        paralelo_id = data.get('paraleloId')
        auth_token = data.get('authToken')

        profesor = request.env['hr.employee'].sudo().search([('id', '=', codigo_profesor)])

        plan_estudios = request.env['ga.plan.estudio'].sudo().search([('materia_id', '=', materia_id), ('grado_id', '=', grado_id)])
        for p_estudio in plan_estudios:
            if not p_estudio.exists(): continue
            paralelo_profesores = request.env['ga.paralelo.profesor'].sudo().search([('paralelo_id', '=', paralelo_id), ('profesor_id', '=', profesor.id)])
            if paralelo_profesores.exists():
                paralelo_profesor = paralelo_profesores[0]
                nowTimeStamp = datetime.time()
                nowDateTime = datetime.fromtimestamp(nowTimeStamp)
                fecha_entrega = nowDateTime + timedelta(hours=1)
                # realizar consulta para ciclo academico respectivo
                ciclo_academico = request.env['ga.ciclo.academico'].sudo().search([])[0] 
                nuevo_actividad_academica = request.env['ga.actividad.academina'].sudo().create({
                    'codigo': 'ACD{}'.format(nowTimeStamp),
                    'descripcion': 'registro de asistencia',
                    'fecha_registro': nowDateTime.strftime('%Y-%m-%d %H:%M:%S'),
                    'fecha_entrega': fecha_entrega.strftime('%Y-%m-%d %H:%M:%S'),
                    'ponderacion' : 0.0,
                    'paralelo_profesosor_id': paralelo_profesor.id,
                    'ciclo_academico_id': ciclo_academico.id
                })
                inscripcion_alumnos = request.env['ga.inscripcion.alumno'].sudo().search([('grado_id','=',grado_id), ('paralelo_id','=', paralelo_id)])
                cant_alumnos_notificados = 0
                for inscripcion_alumno in inscripcion_alumnos:
                    if not inscripcion_alumno.exists(): continue
                    alumno = request.env['ga.alumno'].sudo().search([('id', '=', inscripcion_alumno.alumno_id)])
                    if alumno.exists():
                        alumno = alumno[0]
                        result = Notificacion.sendNotification(auth_token, alumno.token, {
                            'asunto': 'Control de asistencia',
                            'actividadAcademicaId' : nuevo_actividad_academica.id
                        }, {
                            'title': 'Control de asistencia',
                            'body' : 'Control de asistencia para {}'.format(alumno.nombre)
                        })
                        if result : cant_alumnos_notificados = cant_alumnos_notificados + 1
                response_data['notificados'] = cant_alumnos_notificados
        return json.dumps(response_data)

class userController(http.Controller):
    @http.route('/auth/login ', auth='public', type='http', methods=['POST'], csrf=False, website=True)
    def user_auth_login(self, **post):
        body = request.httprequest.data
        data = json.loads(body)
        response_data = {}

        codigo_persona = data.get('codigoPersona')
        notification_token = data.get('tokenMobilNotificacion')

        persona = request.env['ga.alumno'].sudo().search([('codigo','=', codigo_persona)])
        if not persona.exists(): 
            persona = request.env['ga.apoderado'].sudo().search([('codigo','=', codigo_persona)])

        if persona.exists():
            persona.write({
                'token': notification_token
            })
            request.env.cr.commit()
            return json.dumps({
                'usuarioId': persona.Id,
                'nombre': persona.nombre,
                'codigo': persona.codigo,
                'tokenMobil': persona.token
            })
        else:
            return Response(
                json.dumps({'error': 'el codigo no coinside con ningun alumno o apoderado'}),
                status = 500,
                content_type='application/json'
            )
        
        