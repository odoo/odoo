
from odoo import api, fields, models, tools, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import SetDefinitions
from odoo.tools.misc import OrderedSet


#
# Functions for manipulating boolean and selection pseudo-fields
#

class ResGroups(models.Model):
    _name = 'res.groups'
    _description = "Access Groups"
    _rec_name = 'full_name'
    _allow_sudo_commands = False

    name = fields.Char(required=True, translate=True)
    user_ids = fields.Many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', help='Users explicitly in this group')
    all_user_ids = fields.Many2many('res.users', related='user_ids', depends_context=['active_test'], string='Users and implied users')

    model_access = fields.One2many('ir.model.access', 'group_id', string='Access Controls', copy=True)
    rule_groups = fields.Many2many('ir.rule', 'rule_group_rel',
        'group_id', 'rule_group_id', string='Rules', domain="[('global', '=', False)]")
    menu_access = fields.Many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', string='Access Menu')
    view_access = fields.Many2many('ir.ui.view', 'ir_ui_view_group_rel', 'group_id', 'view_id', string='Views')
    comment = fields.Text(translate=True)
    category_id = fields.Many2one('ir.module.category', string='Application', index=True)
    full_name = fields.Char(compute='_compute_full_name', string='Group Name', search='_search_full_name')
    share = fields.Boolean(string='Share Group', help="Group created to set access rights for sharing data with some users.")
    api_key_duration = fields.Float(string='API Keys maximum duration days',
        help="Determines the maximum duration of an api key created by a user belonging to this group.")

    _name_uniq = models.Constraint("UNIQUE (category_id, name)",
        'The name of the group must be unique within an application!')
    _check_api_key_duration = models.Constraint(
        'CHECK(api_key_duration >= 0)',
        'The api key duration cannot be a negative value.',
    )

    @api.constrains('user_ids')
    def _check_one_user_type(self):
        self.user_ids._check_one_user_type()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_settings_group(self):
        classified = self.env['res.config.settings']._get_classified_fields()
        for _name, _groups, implied_group in classified['group']:
            if implied_group.id in self.ids:
                raise ValidationError(_('You cannot delete a group linked with a settings field.'))

    @api.depends('category_id.name', 'name')
    def _compute_full_name(self):
        # Important: value must be stored in environment of group, not group1!
        for group, group1 in zip(self, self.sudo()):
            if group1.category_id:
                group.full_name = '%s / %s' % (group1.category_id.name, group1.name)
            else:
                group.full_name = group1.name

    def _search_full_name(self, operator, operand):
        lst = True
        if isinstance(operand, bool):
            return [('name', operator, operand)]
        if isinstance(operand, str):
            lst = False
            operand = [operand]
        where_domains = []
        for group in operand:
            values = [v for v in group.split('/') if v]
            group_name = values.pop().strip()
            category_name = values and '/'.join(values).strip() or group_name
            group_domain = [('name', operator, lst and [group_name] or group_name)]
            category_ids = self.env['ir.module.category'].sudo()._search(
                [('name', operator, [category_name] if lst else category_name)])
            category_domain = [('category_id', 'in', category_ids)]
            if operator in expression.NEGATIVE_TERM_OPERATORS and not values:
                category_domain = expression.OR([category_domain, [('category_id', '=', False)]])
            if (operator in expression.NEGATIVE_TERM_OPERATORS) == (not values):
                where = expression.AND([group_domain, category_domain])
            else:
                where = expression.OR([group_domain, category_domain])
            where_domains.append(where)
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return expression.AND(where_domains)
        else:
            return expression.OR(where_domains)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        # add explicit ordering if search is sorted on full_name
        if order and order.startswith('full_name'):
            groups = super().search(domain)
            groups = groups.sorted('full_name', reverse=order.endswith('DESC'))
            groups = groups[offset:offset+limit] if limit else groups[offset:]
            return groups._as_query(order)
        return super()._search(domain, offset, limit, order)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for group, vals in zip(self, vals_list):
            vals['name'] = default.get('name') or _('%s (copy)', group.name)
        return vals_list

    def write(self, vals):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise UserError(_('The name of the group can not start with "-"'))
        # invalidate caches before updating groups, since the recomputation of
        # field 'share' depends on method has_group()
        # DLE P139
        if self.ids:
            self.env['ir.model.access'].call_cache_clearing_methods()
        return super().write(vals)

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

#
# Implied groups
#
# Extension of res.groups and res.users with a relation for "implied" or
# "inherited" groups.  Once a user belongs to a group, it automatically belongs
# to the implied groups (transitively).
#

# pylint: disable=E0102
class ResGroups(models.Model):  # noqa: F811
    _inherit = 'res.groups'

    implied_ids = fields.Many2many('res.groups', 'res_groups_implied_rel', 'gid', 'hid',
        string='Inherits', help='Users of this group automatically inherit those groups')
    trans_implied_ids = fields.Many2many('res.groups', string='Transitively inherits',
        compute='_compute_trans_implied', recursive=True)

    @api.depends('implied_ids.trans_implied_ids')
    def _compute_trans_implied(self):
        # Compute the transitive closure recursively. Note that the performance
        # is good, because the record cache behaves as a memo (the field is
        # never computed twice on a given group.)
        for g in self:
            g.trans_implied_ids = g.implied_ids | g.implied_ids.trans_implied_ids

    @api.model_create_multi
    def create(self, vals_list):
        user_ids_list = [vals.pop('user_ids', None) for vals in vals_list]
        groups = super().create(vals_list)
        for group, user_ids in zip(groups, user_ids_list):
            if user_ids:
                # delegate addition of users to add implied groups
                group.write({'user_ids': user_ids})
        self.env.registry.clear_cache('groups')
        return groups

    def write(self, values):
        res = super().write(values)
        if values.get('user_ids') or values.get('implied_ids'):
            # add all implied groups (to all users of each group)
            updated_group_ids = OrderedSet()
            updated_user_ids = OrderedSet()
            for group in self:
                self._cr.execute("""
                    WITH RECURSIVE group_imply(gid, hid) AS (
                        SELECT gid, hid
                          FROM res_groups_implied_rel
                         UNION
                        SELECT i.gid, r.hid
                          FROM res_groups_implied_rel r
                          JOIN group_imply i ON (i.hid = r.gid)
                    )
                    INSERT INTO res_groups_users_rel (gid, uid)
                         SELECT i.hid, r.uid
                           FROM group_imply i, res_groups_users_rel r
                          WHERE r.gid = i.gid
                            AND i.gid = %(gid)s
                         EXCEPT
                         SELECT r.gid, r.uid
                           FROM res_groups_users_rel r
                           JOIN group_imply i ON (r.gid = i.hid)
                          WHERE i.gid = %(gid)s
                    RETURNING gid, uid
                """, dict(gid=group.id))
                updated = self.env.cr.fetchall()
                gids, uids = zip(*updated) if updated else ([], [])
                updated_group_ids.update(gids)
                updated_user_ids.update(uids)
            # notify the ORM about the updated users and groups
            updated_groups = self.env['res.groups'].browse(updated_group_ids)
            updated_groups.invalidate_recordset(['user_ids'])
            updated_groups.modified(['user_ids'])
            updated_users = self.env['res.users'].browse(updated_user_ids)
            updated_users.invalidate_recordset(['groups_id'])
            updated_users.modified(['groups_id'])
            # explicitly check constraints
            updated_groups._validate_fields(['user_ids'])
            updated_users._validate_fields(['groups_id'])
            self._check_one_user_type()
        if 'implied_ids' in values:
            self.env.registry.clear_cache('groups')
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache('groups')
        return res

    def _apply_group(self, implied_group):
        """ Add the given group to the groups implied by the current group
        :param implied_group: the implied group to add
        """
        groups = self.filtered(lambda g: implied_group not in g.implied_ids)
        groups.write({'implied_ids': [Command.link(implied_group.id)]})

    def _remove_group(self, implied_group):
        """ Remove the given group from the implied groups of the current group
        :param implied_group: the implied group to remove
        """
        groups = self.filtered(lambda g: implied_group in g.implied_ids)
        if groups:
            groups.write({'implied_ids': [Command.unlink(implied_group.id)]})
            # if user belongs to implied_group thanks to another group, don't remove him
            # this avoids readding the template user and triggering the mechanism at 121cd0d6084cb28
            users_to_unlink = [
                user
                for user in groups.with_context(active_test=False).user_ids
                if implied_group not in (user.groups_id - implied_group).trans_implied_ids
            ]
            if users_to_unlink:
                # do not remove inactive users (e.g. default)
                implied_group.with_context(active_test=False).write(
                    {'user_ids': [Command.unlink(user.id) for user in users_to_unlink]})

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
            }
            for group in groups
        }
        # determine exclusive groups (will be disjoint for the set expression)
        user_types_category_id = self.env['ir.model.data']._xmlid_to_res_id('base.module_category_user_type', raise_if_not_found=False)
        if user_types_category_id:
            user_type_ids = self.sudo().search([('category_id', '=', user_types_category_id)]).ids
            for user_type_id in user_type_ids:
                data[user_type_id]['disjoints'] = set(user_type_ids) - {user_type_id}

        return SetDefinitions(data)
