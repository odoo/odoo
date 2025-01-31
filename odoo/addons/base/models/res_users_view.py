
import itertools
from collections import defaultdict
from itertools import repeat

from lxml import etree
from lxml.builder import E

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo import api, fields, models, _, Command
from odoo.tools import partition


#
# Functions for manipulating boolean and selection pseudo-fields
#
def is_boolean_group(name):
    return name.startswith('in_group_')

def is_selection_groups(name):
    return name.startswith('sel_groups_')

def is_reified_group(name):
    return is_boolean_group(name) or is_selection_groups(name)

def get_boolean_group(name):
    return int(name[9:])

def get_selection_groups(name):
    return [int(v) for v in name[11:].split('_')]

def name_boolean_group(id):
    return 'in_group_' + str(id)

def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in sorted(ids))

def parse_m2m(commands):
    "return a list of ids corresponding to a many2many value"
    ids = []
    for command in commands:
        if isinstance(command, (tuple, list)):
            if command[0] in (Command.UPDATE, Command.LINK):
                ids.append(command[1])
            elif command[0] == Command.CLEAR:
                ids = []
            elif command[0] == Command.SET:
                ids = list(command[2])
        else:
            ids.append(command)
    return ids


#
# Virtual checkbox and selection for res.user form view
#
# Extension of res.groups and res.users for the special groups view in the users
# form.  This extension presents groups with selection and boolean widgets:
# - Groups are shown by application, with boolean and/or selection fields.
#   Selection fields typically defines a role "Name" for the given application.
# - Uncategorized groups are presented as boolean fields and grouped in a
#   section "Others".
#
# The user form view is modified by an inherited view (base.user_groups_view);
# the inherited view replaces the field 'group_ids' by a set of reified group
# fields (boolean or selection fields).  The arch of that view is regenerated
# each time groups are changed.
#
# Naming conventions for reified groups fields:
# - boolean field 'in_group_ID' is True iff
#       ID is in 'group_ids'
# - selection field 'sel_groups_ID1_..._IDk' is ID iff
#       ID is in 'group_ids' and ID is maximal in the set {ID1, ..., IDk}
#


class ResGroups(models.Model):
    _inherit = 'res.groups'

    color = fields.Integer(string='Color Index')

    @api.model_create_multi
    def create(self, vals_list):
        groups = super().create(vals_list)
        self._update_user_groups_view()
        # actions.get_bindings() depends on action records
        self.env.registry.clear_cache()
        return groups

    def write(self, values):
        # determine which values the "user groups view" depends on
        VIEW_DEPS = ('category_id', 'implied_ids')
        view_values0 = [g[name] for name in VIEW_DEPS if name in values for g in self]
        res = super().write(values)
        # update the "user groups view" only if necessary
        view_values1 = [g[name] for name in VIEW_DEPS if name in values for g in self]
        if view_values0 != view_values1:
            self._update_user_groups_view()
        # actions.get_bindings() depends on action records
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self._update_user_groups_view()
        # actions.get_bindings() depends on action records
        self.env.registry.clear_cache()
        return res

    def _get_hidden_extra_categories(self):
        return ['base.module_category_hidden', 'base.module_category_extra', 'base.module_category_usability']

    @api.model
    def _update_user_groups_view(self):
        """ Modify the view with xmlid ``base.user_groups_view``, which inherits
            the user form view, and introduces the reified group fields.
        """
        # remove the language to avoid translations, it will be handled at the view level
        self = self.with_context(lang=None)

        # We have to try-catch this, because at first init the view does not
        # exist but we are already creating some basic groups.
        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        if not (view and view._name == 'ir.ui.view'):
            return

        if self._context.get('install_filename') or self._context.get(MODULE_UNINSTALL_FLAG):
            # use a dummy view during install/upgrade/uninstall
            xml = E.field(name="group_ids", position="after")

        else:
            group_no_one = view.env.ref('base.group_no_one')
            group_employee = view.env.ref('base.group_user')
            xml0, xml1, xml2, xml3, xml4 = [], [], [], [], []
            xml_by_category = {}
            xml1.append(E.separator(string='User Type', colspan="2", groups='base.group_no_one'))

            user_type_field_name = ''
            user_type_readonly = str({})
            sorted_tuples = sorted(self.get_groups_by_application(),
                                   key=lambda t: t[0].xml_id != 'base.module_category_user_type')

            invisible_information = "All fields linked to groups must be present in the view due to the overwrite of create and write. The implied groups are calculated using this values."

            for app, kind, gs, category_name in sorted_tuples:  # we process the user type first
                attrs = {}
                # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
                if app.xml_id in self._get_hidden_extra_categories():
                    attrs['groups'] = 'base.group_no_one'

                # User type (employee, portal or public) is a separated group. This is the only 'selection'
                # group of res.groups without implied groups (with each other).
                if app.xml_id == 'base.module_category_user_type':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    # test_reified_groups, put the user category type in invisible
                    # as it's used in domain of attrs of other fields,
                    # and the normal user category type field node is wrapped in a `groups="base.no_one"`,
                    # and is therefore removed when not in debug mode.
                    xml0.append(E.field(name=field_name, invisible="True", on_change="1"))
                    xml0.append(etree.Comment(invisible_information))
                    user_type_field_name = field_name
                    user_type_readonly = f'{user_type_field_name} != {group_employee.id}'
                    attrs['widget'] = 'radio'
                    # Trigger the on_change of this "virtual field"
                    attrs['on_change'] = '1'
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())

                elif kind == 'selection':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    attrs['readonly'] = user_type_readonly
                    attrs['on_change'] = '1'
                    if category_name not in xml_by_category:
                        xml_by_category[category_name] = []
                        xml_by_category[category_name].append(E.newline())
                    xml_by_category[category_name].append(E.field(name=field_name, **attrs))
                    xml_by_category[category_name].append(E.newline())
                    # add duplicate invisible field so default values are saved on create
                    if attrs.get('groups') == 'base.group_no_one':
                        xml0.append(E.field(name=field_name, **dict(attrs, invisible="True", groups='!base.group_no_one')))
                        xml0.append(etree.Comment(invisible_information))

                else:
                    # application separator with boolean fields
                    app_name = app.name or 'Other'
                    xml4.append(E.separator(string=app_name, **attrs))
                    left_group, right_group = [], []
                    attrs['readonly'] = user_type_readonly
                    # we can't use enumerate, as we sometime skip groups
                    group_count = 0
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        dest_group = left_group if group_count % 2 == 0 else right_group
                        if g == group_no_one:
                            # make the group_no_one invisible in the form view
                            dest_group.append(E.field(name=field_name, invisible="True", **attrs))
                            dest_group.append(etree.Comment(invisible_information))
                        else:
                            dest_group.append(E.field(name=field_name, **attrs))
                        # add duplicate invisible field so default values are saved on create
                        xml0.append(E.field(name=field_name, **dict(attrs, invisible="True", groups='!base.group_no_one')))
                        xml0.append(etree.Comment(invisible_information))
                        group_count += 1
                    xml4.append(E.group(*left_group))
                    xml4.append(E.group(*right_group))

            xml4.append({'class': "o_label_nowrap"})
            user_type_invisible = f'{user_type_field_name} != {group_employee.id}' if user_type_field_name else None

            for xml_cat in sorted(xml_by_category.keys(), key=lambda it: it[0]):
                master_category_name = xml_cat[1]
                xml3.append(E.group(*(xml_by_category[xml_cat]), string=master_category_name))

            field_name = 'user_group_warning'
            user_group_warning_xml = E.div({
                'class': "alert alert-warning",
                'role': "alert",
                'colspan': "2",
                'invisible': f'not {field_name}',
            })
            user_group_warning_xml.append(E.label({
                'for': field_name,
                'string': "Access Rights Mismatch",
                'class': "text text-warning fw-bold",
            }))
            user_group_warning_xml.append(E.field(name=field_name))
            xml2.append(user_group_warning_xml)

            xml = E.field(
                *(xml0),
                E.group(*(xml1), groups="base.group_no_one"),
                E.group(*(xml2), invisible=user_type_invisible),
                E.group(*(xml3), invisible=user_type_invisible),
                E.group(*(xml4), invisible=user_type_invisible, groups="base.group_no_one"), name="group_ids", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))

        # serialize and update the view
        xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")
        if xml_content != view.arch:  # avoid useless xml validation if no change
            new_context = dict(view._context)
            new_context.pop('install_filename', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})

    def get_application_groups(self, domain):
        """ Return the non-share groups that satisfy ``domain``. """
        return self.search(domain + [('share', '=', False)])

    @api.model
    def get_groups_by_application(self):
        """ Return all groups classified by application (module category), as a list::

                [(app, kind, groups), ...],

            where ``app`` and ``groups`` are recordsets, and ``kind`` is either
            ``'boolean'`` or ``'selection'``. Applications are given in sequence
            order.  If ``kind`` is ``'selection'``, ``groups`` are given in
            reverse implication order.
        """
        def linearize(app, gs, category_name):
            # 'User Type' is an exception
            if app.xml_id == 'base.module_category_user_type':
                return (app, 'selection', gs.sorted('id'), category_name)
            # determine sequence order: a group appears after its implied groups
            order = {g: len(g.all_implied_ids & gs) for g in gs}
            # We want a selection for Accounting too. Auditor and Invoice are both
            # children of Accountant, but the two of them make a full accountant
            # so it makes no sense to have checkboxes.
            if app.xml_id == 'base.module_category_accounting_accounting':
                return (app, 'selection', gs.sorted(key=order.get), category_name)
            # check whether order is total, i.e., sequence orders are distinct
            if len(set(order.values())) == len(gs):
                return (app, 'selection', gs.sorted(key=order.get), category_name)
            else:
                return (app, 'boolean', gs, (100, 'Other'))

        # classify all groups by application
        by_app, others = defaultdict(self.browse), self.browse()
        for g in self.get_application_groups([]):
            if g.category_id:
                by_app[g.category_id] += g
            else:
                others += g
        # build the result
        res = []
        for app, gs in sorted(by_app.items(), key=lambda it: it[0].sequence or 0):
            if app.parent_id:
                res.append(linearize(app, gs, (app.parent_id.sequence, app.parent_id.name)))
            else:
                res.append(linearize(app, gs, (100, 'Other')))

        if others:
            res.append((self.env['ir.module.category'], 'boolean', others, (100,'Other')))
        return res


class UsersView(models.Model):
    _inherit = 'res.users'

    user_group_warning = fields.Text(string="User Group Warning", compute="_compute_user_group_warning")

    @api.depends('group_ids', 'share')
    @api.depends_context('show_user_group_warning')
    def _compute_user_group_warning(self):
        self.user_group_warning = False
        if self._context.get('show_user_group_warning'):
            for user in self.filtered_domain([('share', '=', False)]):
                group_inheritance_warnings = self._prepare_warning_for_group_inheritance(user)
                if group_inheritance_warnings:
                    user.user_group_warning = group_inheritance_warnings

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for values in vals_list:
            new_vals_list.append(self._remove_reified_groups(values))
        return super().create(new_vals_list)

    def write(self, values):
        values = self._remove_reified_groups(values)
        return super().write(values)

    @api.model
    def new(self, values=None, origin=None, ref=None):
        if values is None:
            values = {}
        values = self._remove_reified_groups(values)
        return super().new(values=values, origin=origin, ref=ref)

    def _prepare_warning_for_group_inheritance(self, user):
        """ Check (updated) groups configuration for user. If implieds groups
        will be added back due to inheritance and hierarchy in groups return
        a message explaining the missing groups.

        :param res.users user: target user

        :return: string to display in a warning
        """
        # Current groups of the user
        current_groups = user.group_ids.filtered('implied_ids')
        current_groups_by_category = defaultdict(lambda: self.env['res.groups'])
        for group in current_groups.all_implied_ids:
            in_category = group.all_implied_ids.filtered(lambda g: g.category_id == group.category_id)
            current_groups_by_category[group.category_id] |= in_category - group

        missing_groups = {}
        # We don't want to show warning for "Technical" and "Extra Rights" groups
        categories_to_ignore = self.env.ref('base.module_category_hidden') + self.env.ref('base.module_category_usability')
        for group in current_groups:
            # Get the updated group from current groups
            missing_implied_groups = group.implied_ids - user.group_ids
            # Get the missing group needed in updated group's category (For example, someone changes
            # Sales: Admin to Sales: User, but Field Service is already set to Admin, so here in the
            # 'Sales' category, we will at the minimum need Admin group)
            missing_implied_groups = missing_implied_groups.filtered(
                lambda g:
                g.category_id not in (group.category_id | categories_to_ignore) and
                g not in current_groups_by_category[g.category_id] and
                (self.env.user.has_group('base.group_no_one') or g.category_id)
            )
            if missing_implied_groups:
                # prepare missing group message, by categories
                missing_groups[group] = ", ".join(
                    f'"{missing_group.category_id.name or self.env._("Other")}: {missing_group.name}"'
                    for missing_group in missing_implied_groups
                )
        return "\n".join(
            self.env._(
                'Since %(user)s is a/an "%(category)s: %(group)s", they will at least obtain the right %(missing_group_message)s',
                user=user.name,
                category=group.category_id.name or self.env._('Other'),
                group=group.name,
                missing_group_message=missing_group_message,
            ) for group, missing_group_message in missing_groups.items()
        )

    def _remove_reified_groups(self, values):
        """ return `values` without reified group fields """
        add, rem = [], []
        values1 = {}

        for key, val in values.items():
            if is_boolean_group(key):
                (add if val else rem).append(get_boolean_group(key))
            elif is_selection_groups(key):
                rem += get_selection_groups(key)
                if val:
                    add.append(val)
            else:
                values1[key] = val

        if 'group_ids' not in values and (add or rem):
            added = self.env['res.groups'].sudo().browse(add).all_implied_ids
            added_ids = added._ids
            # remove group ids in `rem` and add group ids in `add`
            # do not remove groups that are added by implied
            values1['group_ids'] = list(itertools.chain(
                zip(repeat(3), [gid for gid in rem if gid not in added_ids]),
                zip(repeat(4), add)
            ))

        return values1

    @api.model
    def default_get(self, fields):
        group_fields, fields = partition(is_reified_group, fields)
        fields1 = (fields + ['group_ids']) if group_fields else fields
        values = super().default_get(fields1)
        self._add_reified_groups(group_fields, values)
        return values

    def _determine_fields_to_fetch(self, field_names, ignore_when_in_cache=False):
        valid_fields = partition(is_reified_group, field_names)[1]
        return super()._determine_fields_to_fetch(valid_fields, ignore_when_in_cache)

    def _read_format(self, fnames, load='_classic_read'):
        valid_fields = partition(is_reified_group, fnames)[1]
        return super()._read_format(valid_fields, load)

    def onchange(self, values, field_names, fields_spec):
        reified_fnames = [fname for fname in fields_spec if is_reified_group(fname)]
        if reified_fnames:
            values = {key: val for key, val in values.items() if key != 'group_ids'}
            values = self._remove_reified_groups(values)

            if any(is_reified_group(fname) for fname in field_names):
                field_names = [fname for fname in field_names if not is_reified_group(fname)]
                field_names.append('group_ids')

            fields_spec = {
                field_name: field_spec
                for field_name, field_spec in fields_spec.items()
                if not is_reified_group(field_name)
            }
            fields_spec['group_ids'] = {}

        result = super().onchange(values, field_names, fields_spec)

        if reified_fnames and 'group_ids' in result.get('value', {}):
            self._add_reified_groups(reified_fnames, result['value'])
            result['value'].pop('group_ids', None)

        return result

    def read(self, fields=None, load='_classic_read'):
        # determine whether reified groups fields are required, and which ones
        fields1 = fields or list(self.fields_get())
        group_fields, other_fields = partition(is_reified_group, fields1)

        # read regular fields (other_fields); add 'group_ids' if necessary
        drop_groups_id = False
        if group_fields and fields:
            if 'group_ids' not in other_fields:
                other_fields.append('group_ids')
                drop_groups_id = True
        else:
            other_fields = fields

        res = super().read(other_fields, load=load)

        # post-process result to add reified group fields
        if group_fields:
            for values in res:
                self._add_reified_groups(group_fields, values)
                if drop_groups_id:
                    values.pop('group_ids', None)
        return res

    def _add_reified_groups(self, fields, values):
        """ add the given reified group fields into `values` """
        gids = set(parse_m2m(values.get('group_ids') or []))
        for f in fields:
            if is_boolean_group(f):
                values[f] = get_boolean_group(f) in gids
            elif is_selection_groups(f):
                # determine selection groups, in order
                sel_groups = self.env['res.groups'].sudo().browse(get_selection_groups(f))
                sel_order = {g: len(g.all_implied_ids & sel_groups) for g in sel_groups}
                sel_groups = sel_groups.sorted(key=sel_order.get)
                # determine which ones are in gids
                selected = [gid for gid in sel_groups.ids if gid in gids]
                # if 'Internal User' is in the group, this is the "User Type" group
                # and we need to show 'Internal User' selected, not Public/Portal.
                if self.env.ref('base.group_user').id in selected:
                    values[f] = self.env.ref('base.group_user').id
                else:
                    values[f] = selected and selected[-1] or False

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes=attributes)
        # add reified groups fields
        for app, kind, gs, _category_name in self.env['res.groups'].sudo().get_groups_by_application():
            if kind == 'selection':
                # 'User Type' should not be 'False'. A user is either 'employee', 'portal' or 'public' (required).
                selection_vals = [(False, '')]
                if app.xml_id == 'base.module_category_user_type':
                    selection_vals = []
                field_name = name_selection_groups(gs.ids)
                if allfields and field_name not in allfields:
                    continue
                # selection group field
                tips = []
                if app.description:
                    tips.append(app.description + '\n')
                tips.extend('%s: %s' % (g.name, g.comment) for g in gs if g.comment)
                res[field_name] = {
                    'type': 'selection',
                    'string': app.name or _('Other'),
                    'selection': selection_vals + [(g.id, g.name) for g in gs],
                    'help': '\n'.join(tips),
                    'exportable': False,
                    'selectable': False,
                }
            else:
                # boolean group fields
                for g in gs:
                    field_name = name_boolean_group(g.id)
                    if allfields and field_name not in allfields:
                        continue
                    res[field_name] = {
                        'type': 'boolean',
                        'string': g.name,
                        'help': g.comment,
                        'exportable': False,
                        'selectable': False,
                    }
        return res


class IrModuleCategory(models.Model):
    _inherit = "ir.module.category"

    def write(self, values):
        res = super().write(values)
        if "name" in values:
            self.env["res.groups"]._update_user_groups_view()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["res.groups"]._update_user_groups_view()
        return res
