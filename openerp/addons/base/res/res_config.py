# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from operator import attrgetter
import re

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import ustr
from openerp.tools.translate import _
from openerp import exceptions
from lxml import etree
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


class res_config_module_installation_mixin(object):
    def _install_modules(self, cr, uid, modules, context):
        """Install the requested modules.
            return the next action to execute

          modules is a list of tuples
            (mod_name, browse_record | None)
        """
        ir_module = self.pool.get('ir.module.module')
        to_install_ids = []
        to_install_missing_names = []

        for name, module in modules:
            if not module:
                to_install_missing_names.append(name)
            elif module.state == 'uninstalled':
                to_install_ids.append(module.id)
        result = None
        if to_install_ids:
            result = ir_module.button_immediate_install(cr, uid, to_install_ids, context=context)
        #FIXME: if result is not none, the corresponding todo will be skipped because it was just marked done
        if to_install_missing_names:
            return {
                'type': 'ir.actions.client',
                'tag': 'apps',
                'params': {'modules': to_install_missing_names},
            }

        return result

class res_config_configurable(osv.osv_memory):
    ''' Base classes for new-style configuration items

    Configuration items should inherit from this class, implement
    the execute method (and optionally the cancel one) and have
    their view inherit from the related res_config_view_base view.
    '''
    _name = 'res.config'

    def _next_action(self, cr, uid, context=None):
        Todos = self.pool['ir.actions.todo']
        _logger.info('getting next %s', Todos)

        active_todos = Todos.browse(cr, uid,
            Todos.search(cr, uid, ['&', ('type', '=', 'automatic'), ('state','=','open')]),
                                    context=context)

        user_groups = set(map(
            lambda g: g.id,
            self.pool['res.users'].browse(cr, uid, [uid], context=context)[0].groups_id))

        valid_todos_for_user = [
            todo for todo in active_todos
            if not todo.groups_id or bool(user_groups.intersection((
                group.id for group in todo.groups_id)))
        ]

        if valid_todos_for_user:
            return valid_todos_for_user[0]

        return None

    def _next(self, cr, uid, context=None):
        _logger.info('getting next operation')
        next = self._next_action(cr, uid, context=context)
        _logger.info('next action is %s', next)
        if next:
            return next.action_launch(context=context)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def start(self, cr, uid, ids, context=None):
        return self.next(cr, uid, ids, context)

    def next(self, cr, uid, ids, context=None):
        """ Returns the next todo action to execute (using the default
        sort order)
        """
        return self._next(cr, uid, context=context)

    def execute(self, cr, uid, ids, context=None):
        """ Method called when the user clicks on the ``Next`` button.

        Execute *must* be overloaded unless ``action_next`` is overloaded
        (which is something you generally don't need to do).

        If ``execute`` returns an action dictionary, that action is executed
        rather than just going to the next configuration item.
        """
        raise NotImplementedError(
            'Configuration items need to implement execute')

    def cancel(self, cr, uid, ids, context=None):
        """ Method called when the user click on the ``Skip`` button.

        ``cancel`` should be overloaded instead of ``action_skip``. As with
        ``execute``, if it returns an action dictionary that action is
        executed in stead of the default (going to the next configuration item)

        The default implementation is a NOOP.

        ``cancel`` is also called by the default implementation of
        ``action_cancel``.
        """
        pass

    def action_next(self, cr, uid, ids, context=None):
        """ Action handler for the ``next`` event.

        Sets the status of the todo the event was sent from to
        ``done``, calls ``execute`` and -- unless ``execute`` returned
        an action dictionary -- executes the action provided by calling
        ``next``.
        """
        next = self.execute(cr, uid, ids, context=context)
        if next: return next
        return self.next(cr, uid, ids, context=context)

    def action_skip(self, cr, uid, ids, context=None):
        """ Action handler for the ``skip`` event.

        Sets the status of the todo the event was sent from to
        ``skip``, calls ``cancel`` and -- unless ``cancel`` returned
        an action dictionary -- executes the action provided by calling
        ``next``.
        """
        next = self.cancel(cr, uid, ids, context=context)
        if next: return next
        return self.next(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """ Action handler for the ``cancel`` event. That event isn't
        generated by the res.config.view.base inheritable view, the
        inherited view has to overload one of the buttons (or add one
        more).

        Sets the status of the todo the event was sent from to
        ``cancel``, calls ``cancel`` and -- unless ``cancel`` returned
        an action dictionary -- executes the action provided by calling
        ``next``.
        """
        next = self.cancel(cr, uid, ids, context=context)
        if next: return next
        return self.next(cr, uid, ids, context=context)

class res_config_installer(osv.osv_memory, res_config_module_installation_mixin):
    """ New-style configuration base specialized for addons selection
    and installation.

    Basic usage
    -----------

    Subclasses can simply define a number of _columns as
    fields.boolean objects. The keys (column names) should be the
    names of the addons to install (when selected). Upon action
    execution, selected boolean fields (and those only) will be
    interpreted as addons to install, and batch-installed.

    Additional addons
    -----------------

    It is also possible to require the installation of an additional
    addon set when a specific preset of addons has been marked for
    installation (in the basic usage only, additionals can't depend on
    one another).

    These additionals are defined through the ``_install_if``
    property. This property is a mapping of a collection of addons (by
    name) to a collection of addons (by name) [#]_, and if all the *key*
    addons are selected for installation, then the *value* ones will
    be selected as well. For example::

        _install_if = {
            ('sale','crm'): ['sale_crm'],
        }

    This will install the ``sale_crm`` addon if and only if both the
    ``sale`` and ``crm`` addons are selected for installation.

    You can define as many additionals as you wish, and additionals
    can overlap in key and value. For instance::

        _install_if = {
            ('sale','crm'): ['sale_crm'],
            ('sale','project'): ['sale_service'],
        }

    will install both ``sale_crm`` and ``sale_service`` if all of
    ``sale``, ``crm`` and ``project`` are selected for installation.

    Hook methods
    ------------

    Subclasses might also need to express dependencies more complex
    than that provided by additionals. In this case, it's possible to
    define methods of the form ``_if_%(name)s`` where ``name`` is the
    name of a boolean field. If the field is selected, then the
    corresponding module will be marked for installation *and* the
    hook method will be executed.

    Hook methods take the usual set of parameters (cr, uid, ids,
    context) and can return a collection of additional addons to
    install (if they return anything, otherwise they should not return
    anything, though returning any "falsy" value such as None or an
    empty collection will have the same effect).

    Complete control
    ----------------

    The last hook is to simply overload the ``modules_to_install``
    method, which implements all the mechanisms above. This method
    takes the usual set of parameters (cr, uid, ids, context) and
    returns a ``set`` of addons to install (addons selected by the
    above methods minus addons from the *basic* set which are already
    installed) [#]_ so an overloader can simply manipulate the ``set``
    returned by ``res_config_installer.modules_to_install`` to add or
    remove addons.

    Skipping the installer
    ----------------------

    Unless it is removed from the view, installers have a *skip*
    button which invokes ``action_skip`` (and the ``cancel`` hook from
    ``res.config``). Hooks and additionals *are not run* when skipping
    installation, even for already installed addons.

    Again, setup your hooks accordingly.

    .. [#] note that since a mapping key needs to be hashable, it's
           possible to use a tuple or a frozenset, but not a list or a
           regular set

    .. [#] because the already-installed modules are only pruned at
           the very end of ``modules_to_install``, additionals and
           hooks depending on them *are guaranteed to execute*. Setup
           your hooks accordingly.
    """
    _name = 'res.config.installer'
    _inherit = 'res.config'

    _install_if = {}

    def already_installed(self, cr, uid, context=None):
        """ For each module, check if it's already installed and if it
        is return its name

        :returns: a list of the already installed modules in this
                  installer
        :rtype: [str]
        """
        return map(attrgetter('name'),
                   self._already_installed(cr, uid, context=context))

    def _already_installed(self, cr, uid, context=None):
        """ For each module (boolean fields in a res.config.installer),
        check if it's already installed (either 'to install', 'to upgrade'
        or 'installed') and if it is return the module's record

        :returns: a list of all installed modules in this installer
        :rtype: recordset (collection of Record)
        """
        modules = self.pool['ir.module.module']

        selectable = [field for field in self._columns
                      if type(self._columns[field]) is fields.boolean]
        return modules.browse(
            cr, uid,
            modules.search(cr, uid,
                           [('name','in',selectable),
                            ('state','in',['to install', 'installed', 'to upgrade'])],
                           context=context),
            context=context)

    def modules_to_install(self, cr, uid, ids, context=None):
        """ selects all modules to install:

        * checked boolean fields
        * return values of hook methods. Hook methods are of the form
          ``_if_%(addon_name)s``, and are called if the corresponding
          addon is marked for installation. They take the arguments
          cr, uid, ids and context, and return an iterable of addon
          names
        * additionals, additionals are setup through the ``_install_if``
          class variable. ``_install_if`` is a dict of {iterable:iterable}
          where key and value are iterables of addon names.

          If all the addons in the key are selected for installation
          (warning: addons added through hooks don't count), then the
          addons in the value are added to the set of modules to install
        * not already installed
        """
        base = set(module_name
                   for installer in self.read(cr, uid, ids, context=context)
                   for module_name, to_install in installer.iteritems()
                   if module_name != 'id'
                   if type(self._columns.get(module_name)) is fields.boolean
                   if to_install)

        hooks_results = set()
        for module in base:
            hook = getattr(self, '_if_%s'% module, None)
            if hook:
                hooks_results.update(hook(cr, uid, ids, context=None) or set())

        additionals = set(
            module for requirements, consequences \
                       in self._install_if.iteritems()
                   if base.issuperset(requirements)
                   for module in consequences)

        return (base | hooks_results | additionals).difference(
                    self.already_installed(cr, uid, context))

    def default_get(self, cr, uid, fields_list, context=None):
        ''' If an addon is already installed, check it by default
        '''
        defaults = super(res_config_installer, self).default_get(
            cr, uid, fields_list, context=context)

        return dict(defaults,
                    **dict.fromkeys(
                        self.already_installed(cr, uid, context=context),
                        True))

    def fields_get(self, cr, uid, fields=None, context=None, write_access=True, attributes=None):
        """ If an addon is already installed, set it to readonly as
        res.config.installer doesn't handle uninstallations of already
        installed addons
        """
        fields = super(res_config_installer, self).fields_get(
            cr, uid, fields, context, write_access, attributes)

        for name in self.already_installed(cr, uid, context=context):
            if name not in fields:
                continue
            fields[name].update(
                readonly=True,
                help= ustr(fields[name].get('help', '')) +
                     _('\n\nThis addon is already installed on your system'))
        return fields

    def execute(self, cr, uid, ids, context=None):
        to_install = list(self.modules_to_install(
            cr, uid, ids, context=context))
        _logger.info('Selecting addons %s to install', to_install)

        ir_module = self.pool.get('ir.module.module')
        modules = []
        for name in to_install:
            mod_ids = ir_module.search(cr, uid, [('name', '=', name)])
            record = ir_module.browse(cr, uid, mod_ids[0], context) if mod_ids else None
            modules.append((name, record))

        return self._install_modules(cr, uid, modules, context=context)

class res_config_settings(osv.osv_memory, res_config_module_installation_mixin):
    """ Base configuration wizard for application settings.  It provides support for setting
        default values, assigning groups to employee users, and installing modules.
        To make such a 'settings' wizard, define a model like::

            class my_config_wizard(osv.osv_memory):
                _name = 'my.settings'
                _inherit = 'res.config.settings'
                _columns = {
                    'default_foo': fields.type(..., default_model='my.model'),
                    'group_bar': fields.boolean(..., group='base.group_user', implied_group='my.group'),
                    'module_baz': fields.boolean(...),
                    'other_field': fields.type(...),
                }

        The method ``execute`` provides some support based on a naming convention:

        *   For a field like 'default_XXX', ``execute`` sets the (global) default value of
            the field 'XXX' in the model named by ``default_model`` to the field's value.

        *   For a boolean field like 'group_XXX', ``execute`` adds/removes 'implied_group'
            to/from the implied groups of 'group', depending on the field's value.
            By default 'group' is the group Employee.  Groups are given by their xml id.
            The attribute 'group' may contain several xml ids, separated by commas.

        *   For a selection field like 'group_XXX' composed of 2 integers values ('0' and '1'),
            ``execute`` adds/removes 'implied_group' to/from the implied groups of 'group', 
            depending on the field's value.
            By default 'group' is the group Employee.  Groups are given by their xml id.
            The attribute 'group' may contain several xml ids, separated by commas.

        *   For a boolean field like 'module_XXX', ``execute`` triggers the immediate
            installation of the module named 'XXX' if the field has value ``True``.

        *   For a selection field like 'module_XXX' composed of 2 integers values ('0' and '1'), 
            ``execute`` triggers the immediate installation of the module named 'XXX' 
            if the field has the integer value ``1``.

        *   For the other fields, the method ``execute`` invokes all methods with a name
            that starts with 'set_'; such methods can be defined to implement the effect
            of those fields.

        The method ``default_get`` retrieves values that reflect the current status of the
        fields like 'default_XXX', 'group_XXX' and 'module_XXX'.  It also invokes all methods
        with a name that starts with 'get_default_'; such methods can be defined to provide
        current values for other fields.
    """
    _name = 'res.config.settings'

    def copy(self, cr, uid, id, values, context=None):
        raise UserError(_("Cannot duplicate configuration!"), "")

    def fields_view_get(self, cr, user, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        ret_val = super(res_config_settings, self).fields_view_get(
            cr, user, view_id=view_id, view_type=view_type, context=context,
            toolbar=toolbar, submenu=submenu)

        can_install_modules = self.pool['ir.module.module'].check_access_rights(
                                    cr, user, 'write', raise_exception=False)

        doc = etree.XML(ret_val['arch'])

        for field in ret_val['fields']:
            if not field.startswith("module_"):
                continue
            for node in doc.xpath("//field[@name='%s']" % field):
                if not can_install_modules:
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                if 'on_change' not in node.attrib:
                    node.set("on_change",
                    "onchange_module(%s, '%s')" % (field, field))

        ret_val['arch'] = etree.tostring(doc)
        return ret_val

    def onchange_module(self, cr, uid, ids, field_value, module_name, context=None):
        module_pool = self.pool.get('ir.module.module')
        module_ids = module_pool.search(
            cr, SUPERUSER_ID, [('name', '=', module_name.replace("module_", '')),
            ('state','in', ['to install', 'installed', 'to upgrade'])],
            context=context)

        if module_ids and not field_value:
            dep_ids = module_pool.downstream_dependencies(cr, SUPERUSER_ID, module_ids, context=context)
            dep_name = [x.shortdesc for x  in module_pool.browse(
                cr, SUPERUSER_ID, dep_ids + module_ids, context=context)]
            message = '\n'.join(dep_name)
            return {
                'warning': {
                    'title': _('Warning!'),
                    'message': _('Disabling this option will also uninstall the following modules \n%s') % message,
                }
            }
        return {}

    def _get_classified_fields(self, cr, uid, context=None):
        """ return a dictionary with the fields classified by category::

                {   'default': [('default_foo', 'model', 'foo'), ...],
                    'group':   [('group_bar', [browse_group], browse_implied_group), ...],
                    'module':  [('module_baz', browse_module), ...],
                    'other':   ['other_field', ...],
                }
        """
        ir_model_data = self.pool['ir.model.data']
        ir_module = self.pool['ir.module.module']
        def ref(xml_id):
            mod, xml = xml_id.split('.', 1)
            return ir_model_data.get_object(cr, uid, mod, xml, context=context)

        defaults, groups, modules, others = [], [], [], []
        for name, field in self._columns.items():
            if name.startswith('default_') and hasattr(field, 'default_model'):
                defaults.append((name, field.default_model, name[8:]))
            elif name.startswith('group_') and (isinstance(field, fields.boolean) or isinstance(field, fields.selection)) \
                 and hasattr(field, 'implied_group'):
                field_groups = getattr(field, 'group', 'base.group_user').split(',')
                groups.append((name, map(ref, field_groups), ref(field.implied_group)))
            elif name.startswith('module_') and (isinstance(field, fields.boolean) or isinstance(field, fields.selection)):
                mod_ids = ir_module.search(cr, SUPERUSER_ID, [('name', '=', name[7:])])
                record = ir_module.browse(cr, SUPERUSER_ID, mod_ids[0], context) if mod_ids else None
                modules.append((name, record))
            else:
                others.append(name)

        return {'default': defaults, 'group': groups, 'module': modules, 'other': others}

    def default_get(self, cr, uid, fields, context=None):
        ir_values = self.pool['ir.values']
        classified = self._get_classified_fields(cr, uid, context)

        res = super(res_config_settings, self).default_get(cr, uid, fields, context)

        # defaults: take the corresponding default value they set
        for name, model, field in classified['default']:
            value = ir_values.get_default(cr, uid, model, field)
            if value is not None:
                res[name] = value

        # groups: which groups are implied by the group Employee
        for name, groups, implied_group in classified['group']:
            res[name] = all(implied_group in group.implied_ids for group in groups)
            if self._fields[name].type == 'selection':
                res[name] = int(res[name])

        # modules: which modules are installed/to install
        for name, module in classified['module']:
            res[name] = False if not module else module.state in ('installed', 'to install', 'to upgrade')
            if self._fields[name].type == 'selection':
                res[name] = int(res[name])

        # other fields: call all methods that start with 'get_default_'
        for method in dir(self):
            if method.startswith('get_default_'):
                res.update(getattr(self, method)(cr, uid, fields, context))

        return res

    def execute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        context = dict(context, active_test=False)
        if not self.pool['res.users']._is_admin(cr, uid, [uid]):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))

        ir_values = self.pool['ir.values']
        ir_module = self.pool['ir.module.module']
        res_groups = self.pool['res.groups']

        classified = self._get_classified_fields(cr, uid, context=context)

        config = self.browse(cr, uid, ids[0], context)

        # default values fields
        for name, model, field in classified['default']:
            ir_values.set_default(cr, SUPERUSER_ID, model, field, config[name])

        # group fields: modify group / implied groups
        for name, groups, implied_group in classified['group']:
            gids = map(int, groups)
            if config[name]:
                res_groups.write(cr, uid, gids, {'implied_ids': [(4, implied_group.id)]}, context=context)
            else:
                res_groups.write(cr, uid, gids, {'implied_ids': [(3, implied_group.id)]}, context=context)
                uids = set()
                for group in groups:
                    uids.update(map(int, group.users))
                implied_group.write({'users': [(3, u) for u in uids]})

        # other fields: execute all methods that start with 'set_'
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, ids, context)

        # module fields: install/uninstall the selected modules
        to_install = []
        to_uninstall_ids = []
        lm = len('module_')
        for name, module in classified['module']:
            if config[name]:
                to_install.append((name[lm:], module))
            else:
                if module and module.state in ('installed', 'to upgrade'):
                    to_uninstall_ids.append(module.id)

        if to_uninstall_ids:
            ir_module.button_immediate_uninstall(cr, uid, to_uninstall_ids, context=context)

        action = self._install_modules(cr, uid, to_install, context=context)
        if action:
            return action

        # After the uninstall/install calls, the self.pool is no longer valid.
        # So we reach into the RegistryManager directly.
        res_config = openerp.modules.registry.RegistryManager.get(cr.dbname)['res.config']
        config = res_config.next(cr, uid, [], context=context) or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config

        # force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def cancel(self, cr, uid, ids, context=None):
        # ignore the current record, and send the action to reopen the view
        act_window = self.pool['ir.actions.act_window']
        action_ids = act_window.search(cr, uid, [('res_model', '=', self._name)])
        if action_ids:
            return act_window.read(cr, uid, action_ids[0], [], context=context)
        return {}

    def name_get(self, cr, uid, ids, context=None):
        """ Override name_get method to return an appropriate configuration wizard
        name, and not the generated name."""

        if not ids:
            return []
        # name_get may receive int id instead of an id list
        if isinstance(ids, (int, long)):
            ids = [ids]

        act_window = self.pool['ir.actions.act_window']
        action_ids = act_window.search(cr, uid, [('res_model', '=', self._name)], context=context)
        name = self._name
        if action_ids:
            name = act_window.read(cr, uid, action_ids[0], ['name'], context=context)['name']
        return [(record.id, name) for record in self.browse(cr, uid , ids, context=context)]

    def get_option_path(self, cr, uid, menu_xml_id, context=None):
        """
        Fetch the path to a specified configuration view and the action id to access it.

        :param string menu_xml_id: the xml id of the menuitem where the view is located,
            structured as follows: module_name.menuitem_xml_id (e.g.: "base.menu_sale_config")
        :return tuple:
            - t[0]: string: full path to the menuitem (e.g.: "Settings/Configuration/Sales")
            - t[1]: int or long: id of the menuitem's action
        """
        module_name, menu_xml_id = menu_xml_id.split('.')
        dummy, menu_id = self.pool['ir.model.data'].get_object_reference(cr, uid, module_name, menu_xml_id)
        ir_ui_menu = self.pool['ir.ui.menu'].browse(cr, uid, menu_id, context=context)

        return (ir_ui_menu.complete_name, ir_ui_menu.action.id)

    def get_option_name(self, cr, uid, full_field_name, context=None):
        """
        Fetch the human readable name of a specified configuration option.

        :param string full_field_name: the full name of the field, structured as follows:
            model_name.field_name (e.g.: "sale.config.settings.fetchmail_lead")
        :return string: human readable name of the field (e.g.: "Create leads from incoming mails")
        """
        model_name, field_name = full_field_name.rsplit('.', 1)

        return self.pool[model_name].fields_get(cr, uid, allfields=[field_name], context=context)[field_name]['string']

    def get_config_warning(self, cr, msg, context=None):
        """
        Helper: return a Warning exception with the given message where the %(field:xxx)s
        and/or %(menu:yyy)s are replaced by the human readable field's name and/or menuitem's
        full path.

        Usage:
        ------
        Just include in your error message %(field:model_name.field_name)s to obtain the human
        readable field's name, and/or %(menu:module_name.menuitem_xml_id)s to obtain the menuitem's
        full path.

        Example of use:
        ---------------
        from openerp.addons.base.res.res_config import get_warning_config
        raise get_warning_config(cr, _("Error: this action is prohibited. You should check the field %(field:sale.config.settings.fetchmail_lead)s in %(menu:base.menu_sale_config)s."), context=context)

        This will return an exception containing the following message:
            Error: this action is prohibited. You should check the field Create leads from incoming mails in Settings/Configuration/Sales.

        What if there is another substitution in the message already?
        -------------------------------------------------------------
        You could have a situation where the error message you want to upgrade already contains a substitution. Example:
            Cannot find any account journal of %s type for this company.\n\nYou can create one in the menu: \nConfiguration\Journals\Journals.
        What you want to do here is simply to replace the path by %menu:account.menu_account_config)s, and leave the rest alone.
        In order to do that, you can use the double percent (%%) to escape your new substitution, like so:
            Cannot find any account journal of %s type for this company.\n\nYou can create one in the %%(menu:account.menu_account_config)s.
        """

        res_config_obj = openerp.registry(cr.dbname)['res.config.settings']
        regex_path = r'%\(((?:menu|field):[a-z_\.]*)\)s'

        # Process the message
        # 1/ find the menu and/or field references, put them in a list
        references = re.findall(regex_path, msg, flags=re.I)

        # 2/ fetch the menu and/or field replacement values (full path and
        #    human readable field's name) and the action_id if any
        values = {}
        action_id = None
        for item in references:
            ref_type, ref = item.split(':')
            if ref_type == 'menu':
                values[item], action_id = res_config_obj.get_option_path(cr, SUPERUSER_ID, ref, context=context)
            elif ref_type == 'field':
                values[item] = res_config_obj.get_option_name(cr, SUPERUSER_ID, ref, context=context)

        # 3/ substitute and return the result
        if (action_id):
            return exceptions.RedirectWarning(msg % values, action_id, _('Go to the configuration panel'))
        return exceptions.UserError(msg % values)
