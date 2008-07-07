##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id: __terp__.py 8595 2008-06-16 13:00:21Z stw $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################

from osv import fields, osv
import pooler

##class config_install_extra_modules(osv.osv_memory):
##    _name='config.install_extra_modules'
##    def _get_uninstall_modules(self,cr,uid,context=None):
##        module_obj=self.pool.get('ir.module.module')
##        line_obj=self.pool.get('config.install_extra_modules.line')
##        uninstall_module_ids=module_obj.search(cr,uid,[('state', 'in', ['uninstalled', 'uninstallable'])])
##        res=[]
##        for id in uninstall_module_ids:
##            res.append(line_obj.create(cr,uid,{'module_id':id},context=None))
##        print res
##        return res
##    _columns = {
##        'name':fields.char('Name', size=64),
##        'module_ids':fields.one2many('config.install_extra_modules.line', 'config_id', 'Modules'),
##
##    }
##    _defaults={
##       'module_ids':_get_uninstall_modules
##    }
##    def action_install(self, cr, uid, ids, context=None):
##        res=self.read(cr,uid,ids)[0]
##        mod_obj = self.pool.get('ir.module.module')
##        line_obj=self.pool.get('config.install_extra_modules.line')
##        if 'module_ids' in res:
##            module_ids=res['module_ids']
##            lines=line_obj.read(cr,uid,module_ids)
##            for line in lines:
##                if 'install' in line and 'module_id' and line and line['install']:
##                    mod_obj.download(cr, uid, [line['module_id']], context=context)
##                    cr.commit()
##                    db, pool = pooler.restart_pool(cr.dbname, update_module=True)
##        return {
##                'view_type': 'form',
##                "view_mode": 'form',
##                'res_model': 'ir.module.module.configuration.wizard',
##                'type': 'ir.actions.act_window',
##                'target':'new',
##            }
##
##config_install_extra_modules()
#
#class config_install_extra_modules_line(osv.osv_memory):
#    _name='config.install_extra_modules.line'
#    _columns = {
#        'name':fields.char('Name', size=64),
#        'install':fields.boolean('Install'),
#        'config_id': fields.many2one('config.install_extra_modules', 'Configuration Module Wizard'),
#        'module_id':fields.many2one('ir.module.module', 'Module',readonly=True,required=True),
#
#    }
#
#
#config_install_extra_modules_line()

class config_install_extra_modules(osv.osv_memory):
    _name='config.install_extra_modules'
    _columns = {
        'name':fields.char('Name', size=64),
        'timesheets_module':fields.boolean('Timesheets module'),
        'holidays_module':fields.boolean('Holidays module'),

    }
    def action_cancel(self,cr,uid,ids,conect=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }
    def action_install(self, cr, uid, ids, context=None):
        res=self.read(cr,uid,ids)[0]
        mod_obj = self.pool.get('ir.module.module')
        if 'timesheets_module' in res and res['timesheets_module']:
            ids = mod_obj.search(cr, uid, [('name', '=', 'hr_timesheet')])
            mod_obj.download(cr, uid, ids, context=context)
            cr.commit()
            #db, pool = pooler.restart_pool(cr.dbname, update_module=True)
        if  'hr_holidays_module' in res and res['hr_holidays_module']:
            ids = mod_obj.search(cr, uid, [('name', '=', 'hr_holidays')])
            mod_obj.download(cr, uid, ids, context=context)
            cr.commit()
            #db, pool = pooler.restart_pool(cr.dbname, update_module=True)
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }

config_install_extra_modules()