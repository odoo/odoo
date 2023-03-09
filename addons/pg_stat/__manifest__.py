{
    'name': 'PostgreSQL Stats',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'sequence': 15,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/pg_indexes.xml',
        'views/pg_stat_activity.xml',
        'views/pg_stat_database.xml',
        'views/pg_stat_tables.xml',
        'views/pg_stats.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
