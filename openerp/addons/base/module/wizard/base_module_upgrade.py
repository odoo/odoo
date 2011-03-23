# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import pooler
from osv import osv, fields
from tools.translate import _

class base_module_upgrade(osv.osv_memory):
    """ Module Upgrade """

    _name = "base.module.upgrade"
    _description = "Module Upgrade"

    _columns = {
        'module_info': fields.text('Modules to update',readonly=True),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view.
        """
        res = super(base_module_upgrade, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        record_id = context and context.get('active_id', False) or False
        active_model = context.get('active_model')
        if (not record_id) or (not active_model):
            return res

        ids = self.get_module_list(cr, uid, context=context)
        if not ids:
            res['arch'] = '''<form string="Apply Scheduled Upgrades">
                                <separator string="System update completed" colspan="4"/>
                                <label align="0.0" string="The selected modules have been updated / installed !" colspan="4"/>
                                <label align="0.0" string="We suggest to reload the menu tab to see the new menus (Ctrl+T then Ctrl+R)." colspan="4"/>
                                 <separator string="" colspan="4"/>
                                <newline/>
                                <button special="cancel" string="Close" icon="gtk-cancel"/>
                                <button name="config" string="Start configuration" type="object" icon="gtk-ok"/>
                             </form>'''

        return res

    def get_module_list(self, cr, uid, context=None):
        mod_obj = self.pool.get('ir.module.module')
        ids = mod_obj.search(cr, uid, [
            ('state', 'in', ['to upgrade', 'to remove', 'to install'])])
        return ids

    def default_get(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        """
        mod_obj = self.pool.get('ir.module.module')
        ids = self.get_module_list(cr, uid, context=context)
        res = mod_obj.read(cr, uid, ids, ['name','state'], context)
        return {'module_info': '\n'.join(map(lambda x: x['name']+' : '+x['state'], res))}

    def upgrade_module(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.module.module')
        ids = mod_obj.search(cr, uid, [('state', 'in', ['to upgrade', 'to remove', 'to install'])])
        unmet_packages = []
        mod_dep_obj = self.pool.get('ir.module.module.dependency')
        for mod in mod_obj.browse(cr, uid, ids):
            depends_mod_ids = mod_dep_obj.search(cr, uid, [('module_id', '=', mod.id)])
            for dep_mod in mod_dep_obj.browse(cr, uid, depends_mod_ids):
                if dep_mod.state in ('unknown','uninstalled'):
                    unmet_packages.append(dep_mod.name)
        if len(unmet_packages):
            raise osv.except_osv(_('Unmet dependency !'), _('Following modules are not installed or unknown: %s') % ('\n\n' + '\n'.join(unmet_packages)))
        mod_obj.download(cr, uid, ids, context=context)
        cr.commit()
        _db, pool = pooler.restart_pool(cr.dbname, update_module=True)

        data_obj = pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'base', 'view_base_module_upgrade_install')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id

        return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'base.module.upgrade',
                'views': [(id2, 'form')],
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def config(self, cr, uid, ids, context=None):
        return self.pool.get('res.config').next(cr, uid, [], context=context)

base_module_upgrade()
