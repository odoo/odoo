
from odoo import api, fields, models, tools


class ResGroups(models.Model):
    _inherit = 'res.groups'
    _order = 'category_id,sequence,name,id'

    sequence = fields.Integer(string='Sequence')
    visible = fields.Boolean(related='category_id.visible', readonly=True)
    color = fields.Integer(string='Color Index')

    @api.model
    @tools.ormcache()
    def _get_view_group_hierarchy(self):
        sections = self.env['ir.module.category'].search([('parent_id', '=', False), ('child_ids.group_ids', '!=', False)], order="sequence")
        privileges = sections.child_ids.filtered(lambda privilege: privilege.group_ids)

        return {
            'groups': {
                group.id: {
                    'id': group.id,
                    'name': group.name,
                    'comment': group.comment,
                    'level': (len(group.all_implied_ids & group.category_id.group_ids) if group.category_id else 0) + group.sequence/1000,
                    'privilege_id': group.category_id.id if group.category_id in privileges else False,
                    'disjoint_ids': group.disjoint_ids.ids,
                    'implied_ids': group.implied_ids.ids,
                    'all_implied_ids': group.all_implied_ids.ids,
                    'all_implied_by_ids': group.all_implied_by_ids.ids,
                }
                for group in self.search([])
            },
            'sections': [
                {
                    'id': section.id,
                    'name': section.name,
                    'privileges': [
                        {
                            'id': privilege.id,
                            'name': privilege.name,
                            'description': privilege.description,
                            'group_ids': [group.id for group in privilege.group_ids.sorted(lambda g: (len(g.all_implied_ids & privilege.group_ids), g.sequence, g.id))]
                        } for privilege in section.child_ids.sorted(lambda c: c.sequence) if privilege.group_ids
                    ]
                } for section in sections
            ]
        }


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _default_view_group_hierarchy(self):
        return self.env['res.groups']._get_view_group_hierarchy()

    view_group_hierarchy = fields.Json(string='Technical field for user group setting', store=False, default=_default_view_group_hierarchy)
