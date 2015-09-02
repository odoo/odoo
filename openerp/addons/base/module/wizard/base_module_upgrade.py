# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError

class base_module_upgrade(osv.osv_memory):
    """ Module Upgrade """

    _name = "base.module.upgrade"
    _description = "Module Upgrade"

    _columns = {
        'module_info': fields.text('Apps to Update',readonly=True),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(base_module_upgrade, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if view_type != 'form':
            return res

        context = {} if context is None else context
        record_id = context and context.get('active_id', False) or False
        active_model = context.get('active_model')
        if (not record_id) or (not active_model):
            return res

        ids = self.get_module_list(cr, uid, context=context)
        if not ids:
            res['arch'] = '''<form string="Upgrade Completed" version="7.0">
                                <separator string="Upgrade Completed" colspan="4"/>
                                <footer>
                                    <button name="config" string="Start Configuration" type="object" class="btn-primary"/>
                                    <button special="cancel" string="Close" class="btn-default"/>
                                </footer>
                             </form>'''

        return res

    def get_module_list(self, cr, uid, context=None):
        mod_obj = self.pool.get('ir.module.module')
        ids = mod_obj.search(cr, uid, [
            ('state', 'in', ['to upgrade', 'to remove', 'to install'])])
        return ids

    def default_get(self, cr, uid, fields, context=None):
        mod_obj = self.pool.get('ir.module.module')
        ids = self.get_module_list(cr, uid, context=context)
        res = mod_obj.read(cr, uid, ids, ['name','state'], context)
        return {'module_info': '\n'.join(map(lambda x: x['name']+' : '+x['state'], res))}

    def upgrade_module_cancel(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.module.module')
        to_installed_ids = mod_obj.search(cr, uid, [
            ('state', 'in', ['to upgrade', 'to remove'])])
        if to_installed_ids:
            mod_obj.write(cr, uid, to_installed_ids, {'state': 'installed'}, context=context)

        to_uninstalled_ids = mod_obj.search(cr, uid, [
            ('state', '=', 'to install')])
        if to_uninstalled_ids:
            mod_obj.write(cr, uid, to_uninstalled_ids, {'state': 'uninstalled'}, context=context)

        return {'type': 'ir.actions.act_window_close'}

    def upgrade_module(self, cr, uid, ids, context=None):
        ir_module = self.pool.get('ir.module.module')

        # install/upgrade: double-check preconditions
        ids = ir_module.search(cr, uid, [('state', 'in', ['to upgrade', 'to install'])])
        if ids:
            cr.execute("""SELECT d.name FROM ir_module_module m
                                        JOIN ir_module_module_dependency d ON (m.id = d.module_id)
                                        LEFT JOIN ir_module_module m2 ON (d.name = m2.name)
                          WHERE m.id in %s and (m2.state IS NULL or m2.state IN %s)""",
                      (tuple(ids), ('uninstalled',)))
            unmet_packages = [x[0] for x in cr.fetchall()]
            if unmet_packages:
                raise UserError(_('Following modules are not installed or unknown: %s') % ('\n\n' + '\n'.join(unmet_packages)))

            ir_module.download(cr, uid, ids, context=context)
            cr.commit() # save before re-creating cursor below

        openerp.api.Environment.reset()
        openerp.modules.registry.RegistryManager.new(cr.dbname, update_module=True)

        return {'type': 'ir.actions.act_window_close'}

    def config(self, cr, uid, ids, context=None):
        return self.pool.get('res.config').next(cr, uid, [], context=context)
