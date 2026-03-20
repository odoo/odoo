# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MRP Subcontracting Repair',
    'category': 'Supply Chain/Repair',
    'description': """
Bridge module between MRP subcontracting and Repair
    """,
    'depends': [
        'mrp_subcontracting', 'repair'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/mrp_subcontracting_repair_security.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
