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
from operator import attrgetter

from osv import osv, fields
from tools.translate import _
import netsvc
from tools import ustr
import pooler


class res_config_configurable(osv.osv_memory):
    ''' Base classes for new-style configuration items

    Configuration items should inherit from this class, implement
    the execute method (and optionally the cancel one) and have
    their view inherit from the related res_config_view_base view.
    '''
    _name = 'res.config'
    _inherit = 'ir.wizard.screen'
    logger = netsvc.Logger()
    __logger = logging.getLogger(_name)

    def get_current_progress(self, cr, uid, context=None):
        '''Return a description the current progress of configuration:
        a tuple of (non_open_todos:int, total_todos: int)
        '''
        return (self.pool.get('ir.actions.todo')\
                .search_count(cr, uid, [('state','<>','open')], context),
                self.pool.get('ir.actions.todo')\
                .search_count(cr, uid, [], context))

    def _progress(self, cr, uid, context=None):
        closed, total = self.get_current_progress(cr, uid, context=context)
        if total:
            return round(closed*100./total)
        return 100.

    _columns = dict(
        progress = fields.float('Configuration Progress', readonly=True),
    )

    _defaults = dict(
        progress = _progress,
    )

    def _next_action(self, cr, uid, context=None):
        todos = self.pool.get('ir.actions.todo')
        self.__logger.info('getting next %s', todos)
        active_todos = todos.search(cr, uid, [('state','=','open')],
                                    limit=1)
        if active_todos:
            todo_obj = todos.browse(cr, uid, active_todos[0], context=None)
            todo_groups = map(lambda x:x.id, todo_obj.groups_id)
            dont_skip_todo = True
            if todo_groups:
                cr.execute("select 1 from res_groups_users_rel where uid=%s and gid IN %s",(uid, tuple(todo_groups),))
                dont_skip_todo = bool(cr.fetchone())
            if dont_skip_todo:
                return todos.browse(cr, uid, active_todos[0], context=None)
            else:
                todos.write(cr, uid, active_todos[0], {'state':'skip'}, context=None)
                return self._next_action(cr, uid)
        return None

    def _set_previous_todo(self, cr, uid, state, context=None):
        """ lookup the previous (which is still the next at this point)
        ir.actions.todo, set it to whatever state was provided.
        """
        # this is ultra brittle, but apart from storing the todo id
        # into the res.config view, I'm not sure how to get the
        # "previous" todo
        previous_todo = self._next_action(cr, uid, context=context)
        if not previous_todo:
            self.__logger.warn(_("Couldn't find previous ir.actions.todo"))
            return
        previous_todo.write({'state':state})

    def _next(self, cr, uid, context=None):
        self.__logger.info('getting next operation')
        next = self._next_action(cr, uid)
        self.__logger.info('next action is %s', next)
        if next:
            action = next.action_id
            return {
                'view_mode': action.view_mode,
                'view_type': action.view_type,
                'view_id': action.view_id and [action.view_id.id] or False,
                'res_model': action.res_model,
                'type': action.type,
                'target': action.target,
            }
        self.__logger.info('all configuration actions have been executed')

        current_user_menu = self.pool.get('res.users')\
            .browse(cr, uid, uid).menu_id
        # return the action associated with the menu
        return self.pool.get(current_user_menu.type)\
            .read(cr, uid, current_user_menu.id)

    def start(self, cr, uid, ids, context=None):
        ids2 = self.pool.get('ir.actions.todo').search(cr, uid, [], context=context)
        for todo in self.pool.get('ir.actions.todo').browse(cr, uid, ids2, context=context):
            if (todo.restart=='always'):
                todo.write({'state':'open'})
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
        self._set_previous_todo(cr, uid, state='done', context=context)
        next = self.execute(cr, uid, ids, context=None)
        if next: return next
        return self.next(cr, uid, ids, context=context)

    def action_skip(self, cr, uid, ids, context=None):
        """ Action handler for the ``skip`` event.

        Sets the status of the todo the event was sent from to
        ``skip``, calls ``cancel`` and -- unless ``cancel`` returned
        an action dictionary -- executes the action provided by calling
        ``next``.
        """
        self._set_previous_todo(cr, uid, state='skip', context=context)
        next = self.cancel(cr, uid, ids, context=None)
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
        self._set_previous_todo(cr, uid, state='cancel', context=context)
        next = self.cancel(cr, uid, ids, context=None)
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
    __logger = logging.getLogger(_name)

    _install_if = {}

    def _already_installed(self, cr, uid, context=None):
        """ For each module (boolean fields in a res.config.installer),
        check if it's already installed (either 'to install', 'to upgrade' or 'installed')
        and if it is, check it by default
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

        return (base | hooks_results | additionals) - set(
            map(attrgetter('name'), self._already_installed(cr, uid, context)))

    def execute(self, cr, uid, ids, context=None):
        modules = self.pool.get('ir.module.module')
        to_install = list(self.modules_to_install(
            cr, uid, ids, context=context))
        self.__logger.info('Selecting addons %s to install', to_install)
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
    __logger = logging.getLogger(_name)

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
        self.__logger.warn(DEPRECATION_MESSAGE)

ir_actions_configuration_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
