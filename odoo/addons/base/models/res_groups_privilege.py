from odoo import fields, models


class ResGroupsPrivilege(models.Model):
    _name = 'res.groups.privilege'
    _description = "Privileges"
    _order = 'sequence, name, id'

    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description')
    placeholder = fields.Char(string='Placeholder', default="No", help="Text that is displayed as placeholder in the selection field of the user form.")
    sequence = fields.Integer(string='Sequence', default=100)
    category_id = fields.Many2one('ir.module.category', string='Category', index=True)
    group_ids = fields.One2many('res.groups', 'privilege_id', string='Groups')
