
from odoo import api, fields, models, tools


class ResGroups(models.Model):
    _inherit = 'res.groups'
    _order = 'category_id,sequence,name'

    sequence = fields.Integer(string='Sequence')
    visible = fields.Boolean(related='category_id.visible', readonly=True)
    color = fields.Integer(string='Color Index')

    # Field used for the widget to define the default group.

    view_group_hierarchy = fields.Json(string='Technical field for default group setting', compute='_compute_view_group_hierarchy')

    def _compute_view_group_hierarchy(self):
        self.view_group_hierarchy = self._get_view_group_hierarchy()

    @api.model
    @tools.ormcache()
    def _get_view_group_hierarchy(self):
        return [
            {
                'id': section.id,
                'name': section.name,
                'categories': [
                    {
                        'id': category.id,
                        'name': category.name,
                        'description': category.description,
                        'groups': [[group.id, group.name] for group in category.group_ids]
                    } for category in section.child_ids.sorted(lambda c: c.sequence) if category.group_ids
                ]
            } for section in self.env['ir.module.category'].search([('parent_id', '=', False), ('child_ids.group_ids', '!=', False)], order="sequence")
        ]


class ResUsers(models.Model):
    _inherit = 'res.users'

    # For "classic" administrators

    def _default_view_group_hierarchy(self):
        return self.env['res.groups']._get_view_group_hierarchy()

    view_group_hierarchy = fields.Json(string='Technical field for user group setting', store=False, default=_default_view_group_hierarchy)

    # For "technical" administrators

    view_disjoint_group_ids = fields.Many2many('res.groups', compute='_compute_view_implied_group_ids', string="Disjoint groups")
    view_all_disjoint_group_ids = fields.Many2many('res.groups', compute='_compute_view_implied_group_ids', string="All disjoint groups")
    view_visible_implied_group_ids = fields.Many2many('res.groups', compute='_compute_view_implied_group_ids', string="Groups added automatically")
    view_show_technical_groups = fields.Boolean(string="Show technical groups", store=False)

    @api.depends('group_ids', 'view_show_technical_groups')
    def _compute_view_implied_group_ids(self):
        group_definitions = self.env['res.groups']._get_group_definitions()

        for user in self:
            view_disjoint_group_ids = user.group_ids.disjoint_ids
            view_all_disjoint_group_ids = group_definitions.get_disjoint_ids(user.all_group_ids.ids)
            view_visible_implied_group_ids = user.group_ids.implied_ids.all_implied_ids
            if not user.view_show_technical_groups:
                view_visible_implied_group_ids = view_visible_implied_group_ids.filtered(lambda g: g.category_id.visible)

            user.view_disjoint_group_ids = view_disjoint_group_ids
            user.view_all_disjoint_group_ids = view_all_disjoint_group_ids
            user.view_visible_implied_group_ids = view_visible_implied_group_ids
