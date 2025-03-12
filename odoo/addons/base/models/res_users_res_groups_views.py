from odoo import api, fields, models, tools, _


class ResGroupsSection(models.Model):
    _name = 'res.groups.section'
    _description = "Security Privilege Sections"
    _order = 'sequence,name,id'

    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=100)
    privilege_ids = fields.One2many('res.groups.privilege', 'section_id', string='Categories')


class ResGroupsPrivilege(models.Model):
    _name = 'res.groups.privilege'
    _description = "Privileges"
    _order = 'sequence,name,id'

    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description', compute="_compute_description")
    placeholder = fields.Char(string='Placeholder', default="No", help="Text that is displayed as placeholder in the selection field of the user form.")
    sequence = fields.Integer(string='Sequence', default=100)
    section_id = fields.Many2one('res.groups.section', string='Group Section')
    group_ids = fields.One2many('res.groups', 'privilege_id', string='Groups')

    @api.depends('group_ids')
    def _compute_description(self):
        for privilege in self:
            privilege.description = '\n'.join(
                self.env._('%(name)s: %(comment)s', name=g.name, comment=g.comment)
                for g in privilege.group_ids if g.comment
            )


class ResGroups(models.Model):
    _inherit = 'res.groups'
    _order = 'privilege_id,sequence,name,id'

    sequence = fields.Integer(string='Sequence')
    privilege_id = fields.Many2one('res.groups.privilege', string='Category')

    _name_uniq = models.Constraint("UNIQUE (privilege_id, name)",
        'The name of the group must be unique within a group privilege!')

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
                        'id': privilege.id,
                        'name': privilege.name,
                        'description': privilege.description,
                        'placeholder': privilege.placeholder,
                        'groups': [[group.id, group.name] for group in privilege.group_ids]
                    } for privilege in section.privilege_ids if privilege.group_ids
                ]
            } for section in self.env['res.groups.section'].search([('privilege_ids.group_ids', '!=', False)])
        ]


class ResUsers(models.Model):
    _inherit = 'res.users'

    role = fields.Selection([('member', 'Member'), ('admin', 'Administrator')], compute='_compute_role', readonly=False, string="Role")

    @api.depends('group_ids')
    def _compute_role(self):
        for user in self:
            if user.has_group('base.group_system'):
                user.role = 'admin'
            elif user.has_group('base.group_user'):
                user.role = 'member'
            else:
                user.role = False

    @api.onchange('role')
    def _set_role_id(self):
        group_admin = self.env.ref('base.group_system')
        group_user = self.env.ref('base.group_user')
        for user in self:
            if user.has_group('base.group_user'):
                groups = user.group_ids.filtered(lambda g: g._origin.id not in (group_user.id, group_admin.id))
                user.group_ids = groups + (group_admin if user.role == 'admin' else group_user)

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
                view_visible_implied_group_ids = view_visible_implied_group_ids.filtered(lambda g: g.privilege_id)

            user.view_disjoint_group_ids = view_disjoint_group_ids
            user.view_all_disjoint_group_ids = view_all_disjoint_group_ids
            user.view_visible_implied_group_ids = view_visible_implied_group_ids
