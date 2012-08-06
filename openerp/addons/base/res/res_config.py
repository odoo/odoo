# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
from operator import attrgetter, itemgetter

from osv import osv, fields
from tools.translate import _
import netsvc
from tools import ustr
import pooler

_logger = logging.getLogger(__name__)

class res_config_configurable(osv.osv_memory):
    ''' Base classes for new-style configuration items

    Configuration items should inherit from this class, implement
    the execute method (and optionally the cancel one) and have
    their view inherit from the related res_config_view_base view.
    '''
    _name = 'res.config'
    _inherit = 'ir.wizard.screen'

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
            res = next.action_launch(context=context)
            res['nodestroy'] = False
            return res
        # reload the client; open the first available root menu
        menu_obj = self.pool.get('ir.ui.menu')
        menu_ids = menu_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu_ids and menu_ids[0] or False},
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

res_config_configurable()

class res_config_installer(osv.osv_memory):
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
            ('sale','project'): ['project_mrp'],
        }

    will install both ``sale_crm`` and ``project_mrp`` if all of
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
        or 'installed') and if it is return the module's browse_record

        :returns: a list of all installed modules in this installer
        :rtype: [browse_record]
        """
        modules = self.pool.get('ir.module.module')

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
                   if type(self._columns[module_name]) is fields.boolean
                   if to_install)

        hooks_results = set()
        for module in base:
            hook = getattr(self, '_if_%s'%(module), None)
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

    def fields_get(self, cr, uid, fields=None, context=None, write_access=True):
        """ If an addon is already installed, set it to readonly as
        res.config.installer doesn't handle uninstallations of already
        installed addons
        """
        fields = super(res_config_installer, self).fields_get(
            cr, uid, fields, context, write_access)

        for name in self.already_installed(cr, uid, context=context):
            if name not in fields:
                continue
            fields[name].update(
                readonly=True,
                help= ustr(fields[name].get('help', '')) +
                     _('\n\nThis addon is already installed on your system'))
        return fields

    def execute(self, cr, uid, ids, context=None):
        modules = self.pool.get('ir.module.module')
        to_install = list(self.modules_to_install(
            cr, uid, ids, context=context))
        _logger.info('Selecting addons %s to install', to_install)
        modules.state_update(
            cr, uid,
            modules.search(cr, uid, [('name','in',to_install)]),
            'to install', ['uninstalled'], context=context)
        cr.commit() #TOFIX: after remove this statement, installation wizard is fail
        new_db, self.pool = pooler.restart_pool(cr.dbname, update_module=True)
res_config_installer()

DEPRECATION_MESSAGE = 'You are using an addon using old-style configuration '\
    'wizards (ir.actions.configuration.wizard). Old-style configuration '\
    'wizards have been deprecated.\n'\
    'The addon should be migrated to res.config objects.'
class ir_actions_configuration_wizard(osv.osv_memory):
    ''' Compatibility configuration wizard

    The old configuration wizard has been replaced by res.config, but in order
    not to break existing but not-yet-migrated addons, the old wizard was
    reintegrated and gutted.
    '''
    _name='ir.actions.configuration.wizard'
    _inherit = 'res.config'

    def _next_action_note(self, cr, uid, ids, context=None):
        next = self._next_action(cr, uid)
        if next:
            # if the next one is also an old-style extension, you never know...
            if next.note:
                return next.note
            return _("Click 'Continue' to configure the next addon...")
        return _("Your database is now fully configured.\n\n"\
            "Click 'Continue' and enjoy your OpenERP experience...")

    _columns = {
        'note': fields.text('Next Wizard', readonly=True),
        }
    _defaults = {
        'note': _next_action_note,
        }

    def execute(self, cr, uid, ids, context=None):
        _logger.warning(DEPRECATION_MESSAGE)

ir_actions_configuration_wizard()



class res_config_settings(osv.osv_memory):
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

        *   For a boolean field like 'module_XXX', ``execute`` triggers the immediate
            installation of the module named 'XXX' if the field has value ``True``.

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
        raise osv.except_osv(_("Cannot duplicate configuration!"), "")

    def _get_classified_fields(self, cr, uid, context=None):
        """ return a dictionary with the fields classified by category::

                {   'default': [('default_foo', 'model', 'foo'), ...],
                    'group':   [('group_bar', browse_group, browse_implied_group), ...],
                    'module':  [('module_baz', browse_module), ...],
                    'other':   ['other_field', ...],
                }
        """
        ir_model_data = self.pool.get('ir.model.data')
        ir_module = self.pool.get('ir.module.module')
        def ref(xml_id):
            mod, xml = xml_id.split('.', 1)
            return ir_model_data.get_object(cr, uid, mod, xml, context)

        defaults, groups, modules, others = [], [], [], []
        for name, field in self._columns.items():
            if name.startswith('default_') and hasattr(field, 'default_model'):
                defaults.append((name, field.default_model, name[8:]))
            elif name.startswith('group_') and isinstance(field, fields.boolean) and hasattr(field, 'implied_group'):
                field_group = getattr(field, 'group', 'base.group_user')
                groups.append((name, ref(field_group), ref(field.implied_group)))
            elif name.startswith('module_') and isinstance(field, fields.boolean):
                mod_ids = ir_module.search(cr, uid, [('name', '=', name[7:])])
                modules.append((name, ir_module.browse(cr, uid, mod_ids[0], context)))
            else:
                others.append(name)

        return {'default': defaults, 'group': groups, 'module': modules, 'other': others}

    def default_get(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        classified = self._get_classified_fields(cr, uid, context)

        res = super(res_config_settings, self).default_get(cr, uid, fields, context)

        # defaults: take the corresponding default value they set
        for name, model, field in classified['default']:
            value = ir_values.get_default(cr, uid, model, field)
            if value is not None:
                res[name] = value

        # groups: which groups are implied by the group Employee
        for name, group, implied_group in classified['group']:
            res[name] = implied_group in group.implied_ids

        # modules: which modules are installed/to install
        for name, module in classified['module']:
            res[name] = module.state in ('installed', 'to install', 'to upgrade')

        # other fields: call all methods that start with 'get_default_'
        for method in dir(self):
            if method.startswith('get_default_'):
                res.update(getattr(self, method)(cr, uid, fields, context))

        return res

    def execute(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        ir_model_data = self.pool.get('ir.model.data')
        ir_module = self.pool.get('ir.module.module')
        res_groups = self.pool.get('res.groups')
        classified = self._get_classified_fields(cr, uid, context)

        config = self.browse(cr, uid, ids[0], context)

        # default values fields
        for name, model, field in classified['default']:
            ir_values.set_default(cr, uid, model, field, config[name])

        # group fields: modify group / implied groups
        for name, group, implied_group in classified['group']:
            if config[name]:
                group.write({'implied_ids': [(4, implied_group.id)]})
            else:
                group.write({'implied_ids': [(3, implied_group.id)]})
                implied_group.write({'users': [(3, u.id) for u in group.users]})

        # other fields: execute all methods that start with 'set_'
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, ids, context)

        # module fields: install/uninstall the selected modules
        to_install_ids = []
        to_uninstall_ids = []
        for name, module in classified['module']:
            if config[name]:
                if module.state == 'uninstalled': to_install_ids.append(module.id)
            else:
                if module.state in ('installed','upgrade'): to_uninstall_ids.append(module.id)

        if to_install_ids or to_uninstall_ids:
            ir_module.button_uninstall(cr, uid, to_uninstall_ids, context=context)
            ir_module.button_immediate_install(cr, uid, to_install_ids, context=context)

        # force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def cancel(self, cr, uid, ids, context=None):
        # ignore the current record, and send the action to reopen the view
        act_window = self.pool.get('ir.actions.act_window')
        action_ids = act_window.search(cr, uid, [('res_model', '=', self._name)])
        if action_ids:
            return act_window.read(cr, uid, action_ids[0], [], context=context)
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
