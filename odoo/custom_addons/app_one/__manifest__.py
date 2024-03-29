{
    'name' : "Reservation de salles",
    'author' : "asma hachaichi",
    'category' : 'reservation',
    'version' : '17.0.1.0',
    'depends' : ['base',
    ],
    'data' : [
        'views/base_name.xml',
        'views/salle_view.xml',
        'views/reservation_view.xml',
        'security/ir.model.access.csv'
    ],
    'application': True,
}