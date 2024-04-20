from odoo.tests.common import TransactionCase

"""
La clase debe de tener el mismo nombre que el modelo

"""
class test_evaluacion(TransactionCase):
    
    # Método para inicializar las variables de la clase
    def setUp(self):
        super(test_evaluacion, self).setUp()
        
    # Función 
    def crear_evaluacion(self, nombre, estado='borrador'):
        # Crear y retornar una evaluación con el nombre y estado proporcionados
        return self.env['evaluacion'].create({
            'nombre': nombre,
            'estado': estado,
        })
        
    # Método para finalizar las pruebas
    def tearDowm(self):
        super(test_evaluacion, self).tearDown()
        return
    
    
    def test_copiar_preguntas_de_template_nom035(self):
        evaluacion = self.crear_evaluacion('Evaluación NOM-035')
        
        # Crear preguntas de ejemplo que podrían ser asociadas a un template
        preguntas = self.env['pregunta'].create([
            {'pregunta_texto': 'Pregunta 1', 'tipo': 'open_question'},
            {'pregunta_texto': 'Pregunta 2',  'tipo': 'open_question'}
        ])
        # Crear un template con preguntas predefinidas
        template = self.env['template'].create({
            'nombre': 'Template NOM-035',
            'tipo': 'nom_035',
            'pregunta_ids': [(6, 0, preguntas.ids)],
        })
        # Simular copia de preguntas desde el template
        evaluacion.pregunta_ids = [(6, 0, template.pregunta_ids.ids)]
        # Verificar que las preguntas se han copiado correctamente
        self.assertEqual(len(evaluacion.pregunta_ids), 2)
        
        
    
    def test_action_nom035(self):
        return
    
    
