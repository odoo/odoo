# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import SetDefinitions


class ResGroups(models.Model):
    _name = 'res.groups'
    _description = "Access Groups"
    _rec_name = 'full_name'
    _allow_sudo_commands = False
    _order = 'privilege_id, sequence, name, id'

    name = fields.Char(required=True, translate=True)
    user_ids = fields.Many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', help='Users explicitly in this group')
    all_user_ids = fields.Many2many('res.users', string='Users and implied users',
        compute='_compute_all_user_ids', search='_search_all_user_ids', inverse='_inverse_all_user_ids')

    all_users_count = fields.Integer('# Users', help='Number of users having this group (implicitly or explicitly)',
        compute='_compute_all_users_count', compute_sudo=True)

    model_access = fields.One2many('ir.model.access', 'group_id', string='Access Controls', copy=True)
    rule_groups = fields.Many2many('ir.rule', 'rule_group_rel',
        'group_id', 'rule_group_id', string='Rules', domain="[('global', '=', False)]")
    menu_access = fields.Many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', string='Access Menu')
    view_access = fields.Many2many('ir.ui.view', 'ir_ui_view_group_rel', 'group_id', 'view_id', string='Views')
    comment = fields.Text(translate=True)
    full_name = fields.Char(compute='_compute_full_name', string='Group Name', search='_search_full_name')
    share = fields.Boolean(string='Share Group', help="Group created to set access rights for sharing data with some users.")
    api_key_duration = fields.Float(string='API Keys maximum duration days',
        help="Determines the maximum duration of an api key created by a user belonging to this group.")

    sequence = fields.Integer(string='Sequence')
    privilege_id = fields.Many2one('res.groups.privilege', string='Privilege', index=True)
    view_group_hierarchy = fields.Json(string='Technical field for default group setting', compute='_compute_view_group_hierarchy')

    _name_uniq = models.Constraint("UNIQUE (privilege_id, name)",
        'The name of the group must be unique within a group privilege!')
    _check_api_key_duration = models.Constraint(
        'CHECK(api_key_duration >= 0)',
        'The api key duration cannot be a negative value.',
    )

    """ The groups involved are to be interpreted as sets.
    Thus we can define groups that we will call for example N, Z... such as mathematical sets.
        ┌──────────────────────────────────────────┐
        │ C  ┌──────────────────────────┐          │
        │    │ R  ┌───────────────────┐ │ ┌──────┐ |   "C"
        │    │    │ Q  ┌────────────┐ │ │ │ I    | |   "I" implied "C"
        │    │    │    │ Z  ┌─────┐ │ │ │ │      | |   "R" implied "C"
        │    │    │    │    │ N   │ │ │ │ │      │ │   "Q" implied "R"
        │    │    │    │    └─────┘ │ │ │ │      │ │   "P" implied "R"
        │    │    │    └────────────┘ │ │ │      │ │   "Z" implied "Q"
        │    │    └───────────────────┘ │ │      │ │   "N" implied "Z"
        │    │      ┌───────────────┐   │ │      │ │
        │    │      │ P             │   │ │      │ │
        │    │      └───────────────┘   │ └──────┘ │
        │    └──────────────────────────┘          │
        └──────────────────────────────────────────┘
    For example:
    * A manager group will imply a user group: all managers are users (like Z imply C);
    * A group "computer developer employee" will imply that he is an employee group, a user
      group, that he has access to the timesheet user group.... "computer developer employee"
      is therefore a set of users in the intersection of these groups. These users will
      therefore have all the rights of these groups in addition to their own access rights.
    """
    implied_ids = fields.Many2many('res.groups', 'res_groups_implied_rel', 'gid', 'hid',
        string='Implied Groups', help='Users of this group are also implicitly part of those groups')
    all_implied_ids = fields.Many2many('res.groups', string='Transitively Implied Groups', recursive=True,
        compute='_compute_all_implied_ids', compute_sudo=True, search='_search_all_implied_ids',
        help="The group itself with all its implied groups.")
    implied_by_ids = fields.Many2many('res.groups', 'res_groups_implied_rel', 'hid', 'gid',
        string='Implying Groups', help="Users in those groups are implicitly part of this group.")
    all_implied_by_ids = fields.Many2many('res.groups', string='Transitively Implying Groups', recursive=True,
        compute='_compute_all_implied_by_ids', compute_sudo=True, search='_search_all_implied_by_ids')
    disjoint_ids = fields.Many2many('res.groups', string='Disjoint Groups',
        help="A user may not belong to this group and one of those.  For instance, users may not be portal users and internal users.",
        compute='_compute_disjoint_ids')

    @api.constrains('implied_ids', 'implied_by_ids')
    def _check_disjoint_groups(self):
        # check for users that might have two exclusive groups
        self.env.registry.clear_cache('groups')
        self.all_implied_by_ids._check_user_disjoint_groups()

    @api.constrains('user_ids')
    def _check_user_disjoint_groups(self):
        # Here we should check all the users in any group of 'self':
        #
        #   self.user_ids._check_disjoint_groups()
        #
        # But that wouldn't scale at all for large groups, like more than 10K
        # users.  So instead we search for such a nasty user.
        gids = self._get_user_type_groups().ids
        domain = (
            Domain('active', '=', True)
            & Domain('group_ids', 'in', self.ids)
            & Domain.OR(
                Domain('all_group_ids', 'in', [gids[index]])
                & Domain('all_group_ids', 'in', gids[index+1:])
                for index in range(0, len(gids) - 1)
            )
        )
        user = self.env['res.users'].search(domain, order='id', limit=1)
        if user:
            user._check_disjoint_groups()  # raises a ValidationError

    @api.ondelete(at_uninstall=False)
    def _unlink_except_settings_group(self):
        classified = self.env['res.config.settings']._get_classified_fields()
        for _name, _groups, implied_group in classified['group']:
            if implied_group.id in self.ids:
                raise ValidationError(self.env._('You cannot delete a group linked with a settings field.'))

    @api.depends('privilege_id.name', 'name')
    @api.depends_context('short_display_name')
    def _compute_full_name(self):
        # Important: value must be stored in environment of group, not group1!
        for group, group1 in zip(self, self.sudo()):
            if group1.privilege_id and not self.env.context.get('short_display_name'):
                group.full_name = '%s / %s' % (group1.privilege_id.name, group1.name)
            else:
                group.full_name = group1.name

    def _search_full_name(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented

        if isinstance(operand, str):
            def make_operand(val): return val
            operands = [operand]
        else:
            def make_operand(val): return [val]
            operands = operand

        where_domains = [Domain('name', operator, operand)]
        for group in operands:
            if not group:
                continue
            domain = Domain('name', operator, make_operand(group))
            where_domains.append(domain)

            if '/' in group:
                privilege_name, _, group_name = group.partition('/')
                group_name = group_name.strip()
                privilege_name = privilege_name.strip()
            else:
                privilege_name = group
                group_name = None

            if privilege_name:
                domain = Domain(
                    'privilege_id', 'any!', Domain('name', operator, make_operand(privilege_name)),
                )
                if group_name:
                    domain &= Domain('name', operator, make_operand(group_name))
                where_domains.append(domain)

        return Domain.OR(where_domains)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        # add explicit ordering if search is sorted on full_name
        if order and order.startswith('full_name'):
            groups = super().search(domain)
            groups = groups.sorted('full_name', reverse=order.endswith('DESC'))
            groups = groups[offset:offset+limit] if limit else groups[offset:]
            return groups._as_query(order)
        return super()._search(domain, offset, limit, order, **kwargs)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for group, vals in zip(self, vals_list):
            vals['name'] = default.get('name') or self.env._('%s (copy)', group.name)
        return vals_list

    def write(self, vals):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise UserError(self.env._('The name of the group can not start with "-"'))

        # invalidate caches before updating groups, since the recomputation of
        # field 'share' depends on method has_group()
        # DLE P139
        if self.ids:
            self.env['ir.model.access'].call_cache_clearing_methods()

        res = super().write(vals)

        if 'implied_ids' in vals or 'implied_by_ids' in vals:
            # Invalidate the cache of groups and their relationships
            self.env.registry.clear_cache('groups')

        return res

    def _ensure_xml_id(self):
        """Return the groups external identifiers, creating the external identifier for groups missing one"""
        result = self.get_external_id()
        missings = {group_id: f'__custom__.group_{group_id}' for group_id, ext_id in result.items() if not ext_id}
        if missings:
            self.env['ir.model.data'].sudo().create(
                [
                    {
                        'name': name.split('.')[1],
                        'model': 'res.groups',
                        'res_id': group_id,
                        'module': name.split('.')[0],
                    }
                    for group_id, name in missings.items()
                ]
            )
            result.update(missings)

        return result

    @api.depends('all_implied_by_ids.user_ids')
    def _compute_all_user_ids(self):
        for group in self.with_context(active_test=False):
            group.all_user_ids = group.all_implied_by_ids.user_ids

    def _inverse_all_user_ids(self):
        for group in self:
            user_to_add = group.all_user_ids - group.all_implied_by_ids.user_ids
            user_to_remove = group.all_implied_by_ids.user_ids - group.all_user_ids
            group.user_ids = group.user_ids - user_to_remove + user_to_add

            cannot_remove = group.all_implied_by_ids.user_ids & user_to_remove
            if cannot_remove:
                raise UserError(self.env._(
                    "It is not possible to remove implied group %(group)s from users %(users)s",
                    group=repr(group.name),
                    users=', '.join(cannot_remove.mapped('name')),
                ))

    def _search_all_user_ids(self, operator, value):
        return [('all_implied_by_ids.user_ids', operator, value)]

    @api.depends('implied_ids.all_implied_ids')
    def _compute_all_implied_ids(self):
        """ Compute the reflexive transitive closure of implied_ids. """
        group_definitions = self._get_group_definitions()
        for g in self:
            g.all_implied_ids = g.ids + group_definitions.get_superset_ids(g.ids)

    def _search_all_implied_ids(self, operator, value):
        """ Compute the search on the reflexive transitive closure of implied_ids. """
        if operator not in ('in', 'not in'):
            return NotImplemented
        group_definitions = self._get_group_definitions()
        ids = [*value, *group_definitions.get_subset_ids(value)]
        return [('id', operator, ids)]

    @api.depends('implied_by_ids.all_implied_by_ids')
    def _compute_all_implied_by_ids(self):
        """ Compute the reflexive transitive closure of implied_by_ids. """
        group_definitions = self._get_group_definitions()
        for g in self:
            g.all_implied_by_ids = g.ids + group_definitions.get_subset_ids(g.ids)

    def _search_all_implied_by_ids(self, operator, value):
        """ Compute the search on the reflexive transitive closure of implied_by_ids. """
        if operator in ("any", "not any") and isinstance(value, Domain):
            value = self.search(value).ids
            operator = "in" if operator == "any" else "not in"
        elif operator not in ('in', 'not in'):
            return NotImplemented

        group_definitions = self._get_group_definitions()
        ids = [*value, *group_definitions.get_superset_ids(value)]

        return [('id', operator, ids)]

    def _get_user_type_groups(self):
        """ Return the (disjoint) user type groups (employee, portal, public). """
        group_ids = [
            gid
            for xid in ('base.group_user', 'base.group_portal', 'base.group_public')
            if (gid := self.env['ir.model.data']._xmlid_to_res_id(xid, raise_if_not_found=False))
        ]
        return self.sudo().browse(group_ids)

    def _compute_disjoint_ids(self):
        user_type_groups = self._get_user_type_groups()
        for group in self:
            if group in user_type_groups:
                group.disjoint_ids = user_type_groups - group
            else:
                group.disjoint_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        groups = super().create(vals_list)
        self.env.registry.clear_cache('groups')
        return groups

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache('groups')
        return res

    def _apply_group(self, implied_group):
        """ Add the given group to the groups implied by the current group
        :param implied_group: the implied group to add
        """
        groups = self.filtered(lambda g: implied_group not in g.all_implied_ids)
        groups.write({'implied_ids': [Command.link(implied_group.id)]})

    def _remove_group(self, implied_group):
        """ Remove the given group from the implied groups of the current group
        :param implied_group: the implied group to remove
        """
        groups = self.all_implied_ids.filtered(lambda g: implied_group in g.implied_ids)
        groups.write({'implied_ids': [Command.unlink(implied_group.id)]})

    def _compute_view_group_hierarchy(self):
        self.view_group_hierarchy = self._get_view_group_hierarchy()

    @api.model
    @tools.ormcache('self.env.lang', cache='groups')
    def _get_view_group_hierarchy(self):
        return {
            'groups': {
                group.id: {
                    'id': group.id,
                    'name': group.name,
                    'comment': group.comment,
                    'privilege_id': group.privilege_id.id,
                    'disjoint_ids': group.disjoint_ids.ids,
                    'implied_ids': group.implied_ids.ids,
                    'all_implied_ids': group.all_implied_ids.ids,
                    'all_implied_by_ids': group.all_implied_by_ids.ids,
                }
                for group in self.search([])
            },
            'privileges': {
                privilege.id: {
                    'id': privilege.id,
                    'name': privilege.name,
                    'category_id': privilege.category_id.id,
                    'description': privilege.description,
                    'placeholder': privilege.placeholder,
                    'group_ids': [group.id for group in privilege.group_ids.sorted(lambda g: (len(g.all_implied_ids & privilege.group_ids) if g.privilege_id else 0, g.sequence, g.id))]
                }
                for privilege in self.env['res.groups.privilege'].search([])
            },
            'categories': [
                {
                    'id': category.id,
                    'name': category.name,
                    'privilege_ids': category.privilege_ids.sorted(lambda p: p.sequence).filtered(lambda p: p.group_ids).ids,
                } for category in self.env['ir.module.category'].search([('privilege_ids.group_ids', '!=', False)])
            ]
        }

    @api.model
    @tools.ormcache(cache='groups')
    def _get_group_definitions(self):
        """ Return the definition of all the groups as a :class:`~odoo.tools.SetDefinitions`. """
        groups = self.sudo().search([], order='id')
        id_to_ref = groups.get_external_id()
        data = {
            group.id: {
                'ref': id_to_ref[group.id] or str(group.id),
                'supersets': group.implied_ids.ids,
                'disjoints': group.disjoint_ids.ids,
            }
            for group in groups
        }
        return SetDefinitions(data)

    @api.model
    def _is_feature_enabled(self, group_reference):
        return self.env['res.users'].sudo().browse(api.SUPERUSER_ID)._has_group(group_reference)

    @api.depends('all_user_ids')
    def _compute_all_users_count(self):
        for group in self:
            group.all_users_count = len(group.all_user_ids)

    def action_show_all_users(self):
        self.ensure_one()
        return {
            'name': self.env._('Users and implied users of %(group)s', group=self.display_name),
            'view_mode': 'list,form',
            'res_model': 'res.users',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False, 'form_view_ref': 'base.view_users_form'},
            'domain': [('all_group_ids', 'in', self.ids)],
            'target': 'current',
        }
