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

from operator import attrgetter

from osv import osv, fields
import netsvc
import pooler

class res_config_configurable(osv.osv_memory):
    ''' Base classes for new-style configuration items

    Configuration items should inherit from this class, implement
    the execute method (and optionally the cancel one) and have
    their view inherit from the related res_config_view_base view.
    '''
    _name = 'res.config'
    logger = netsvc.Logger()

    def _progress(self, cr, uid, context=None):
        total = self.pool.get('ir.actions.todo')\
            .search_count(cr, uid, [], context)
        open = self.pool.get('ir.actions.todo')\
            .search_count(cr, uid, [('active','=',True),
                                    ('state','<>','open')],
                          context)
        if total:
            return round(open*100./total)
        return 100.

    _columns = dict(
        progress=fields.float('Configuration Progress', readonly=True),
        )
    _defaults = dict(
        progress=_progress
        )

    def _next_action(self, cr, uid):
        todos = self.pool.get('ir.actions.todo')
        self.logger.notifyChannel('actions', netsvc.LOG_INFO,
                                  'getting next %s' % todos)
        active_todos = todos.search(cr, uid, [('state','=','open'),
                                              ('active','=',True)],
                                    limit=1, context=None)
        if active_todos:
            return todos.browse(cr, uid, active_todos[0], context=None)
        return None

    def _next(self, cr, uid):
        self.logger.notifyChannel('actions', netsvc.LOG_INFO,
                                  'getting next operation')
        next = self._next_action(cr, uid)
        self.logger.notifyChannel('actions', netsvc.LOG_INFO,
                                  'next action is %s' % next)
        if next:
            self.pool.get('ir.actions.todo').write(cr, uid, next.id, {
                    'state':'done',
                    }, context=None)
            action = next.action_id
            return {
                'view_mode': action.view_mode,
                'view_type': action.view_type,
                'view_id': action.view_id and [action.view_id.id] or False,
                'res_model': action.res_model,
                'type': action.type,
                'target': action.target,
                }
        self.logger.notifyChannel(
            'actions', netsvc.LOG_INFO,
            'all configuration actions have been executed')

        current_user_menu = self.pool.get('res.users')\
            .browse(cr, uid, uid).menu_id
        # return the action associated with the menu
        return self.pool.get(current_user_menu.type)\
            .read(cr, uid, current_user_menu.id)
    def next(self, cr, uid, ids, context=None):
        return self._next(cr, uid)

    def execute(self, cr, uid, ids, context=None):
        raise NotImplementedError(
            'Configuration items need to implement execute')
    def cancel(self, cr, uid, ids, context=None):
        pass

    def action_next(self, cr, uid, ids, context=None):
        next = self.execute(cr, uid, ids, context=None)
        if next: return next
        return self.next(cr, uid, ids, context=context)

    def action_skip(self, cr, uid, ids, context=None):
        next = self.cancel(cr, uid, ids, context=None)
        if next: return next
        return self.next(cr, uid, ids, context=context)
res_config_configurable()

class res_config_installer(osv.osv_memory):
    ''' New-style configuration base specialized for modules selection
    and installation.
    '''
    _name = 'res.config.installer'
    _inherit = 'res.config'

    _install_if = {}

    def _modules_to_install(self, cr, uid, ids, context=None):
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

        return base | hooks_results | additionals

    def default_get(self, cr, uid, fields_list, context=None):
        modules = self.pool.get('ir.module.module')
        defaults = super(res_config_installer, self).default_get(
            cr, uid, fields_list, context=context)

        selectable = [field for field in self._columns
                      if type(self._columns[field]) is fields.boolean]
        already_installed = modules.browse(
            cr, uid,
            modules.search(cr, uid,
                           [('name','in',selectable),
                            ('state','not in',['uninstallable', 'uninstalled'])],
                           context=context),
            context=context)

        return dict(defaults,
                    **dict.fromkeys(
                        map(attrgetter('name'), already_installed),
                        True))

    def execute(self, cr, uid, ids, context=None):
        modules = self.pool.get('ir.module.module')
        to_install = list(self._modules_to_install(
            cr, uid, ids, context=context))
        self.logger.notifyChannel(
            'installer', netsvc.LOG_INFO,
            'Selecting addons %s to install'%to_install)
        modules.state_update(
            cr, uid,
            modules.search(cr, uid, [('name','in',to_install)]),
            'to install', ['uninstalled'], context=context)
        cr.commit()

        pooler.restart_pool(cr.dbname, update_module=True)
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
            return "Click 'Continue' to configure the next addon..."
        return "Your database is now fully configured.\n\n"\
            "Click 'Continue' and enjoy your OpenERP experience..."

    _columns = {
        'note': fields.text('Next Wizard', readonly=True),
        }
    _defaults = {
        'note': _next_action_note,
        }

    def execute(self, cr, uid, ids, context=None):
        self.logger.notifyChannel(
            'configuration', netsvc.LOG_WARNING, DEPRECATION_MESSAGE)

ir_actions_configuration_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
