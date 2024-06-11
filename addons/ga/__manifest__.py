{
    'name': 'Gestion Academica',
    'version': '1.0',
    'category': 'CRM',
    'license': 'AGPL-3',
    'description': """
        Este es un modulo para la gestion de diferentes academia de enseñanza
    """,
    'author': 'Gestion Academica',
    'website': 'ga',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/ga_menu_view.xml',
        'views/ga_actividad_academica.xml',
        'views/ga_alumno_view.xml',
        'views/ga_apoderado_view.xml',
        'views/ga_chofer_view.xml',
        'views/ga_inscripcion_view.xml',
        'views/ga_registro_academico.xml',
        'views/ga_ruta_chofer_view.xml',
        'views/ga_rutas_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}