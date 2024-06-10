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
        'views/ga_inscripcion_views.xml',
       
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}