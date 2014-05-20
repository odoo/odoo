
{
    'name': 'HR Material',
    'version': '1.0',
    'description': """
        Track material's employees and manage material allocation """,
    'author': 'OpenERP SA',
    'depends': ['hr'],
    'demo': ['data/hr_material_demo.xml'],
    'test': [],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/hr_material_view.xml',
        'views/hr_material.xml',
        'data/hr_material_data.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

