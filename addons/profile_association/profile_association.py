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


class profile_association_config_install_modules_wizard(osv.osv_memory):
    _name='profile.association.config.install_modules_wizard'
    _columns = {
        'crm_configuration':fields.boolean('CRM & Calendars', help="This installs the customer relationship features like: leads and opportunities tracking, shared calendar, jobs tracking, bug tracker, and so on."),
        'hr_expense':fields.boolean('Expenses Tracking', help="Tracks the personal expenses process, from the employee expense encoding, to the reimbursement of the employee up to the reinvoicing to the final customer."),
        'project':fields.boolean('Project Management'),
        'event' : fields.boolean('Events Organisation'),
        'crm' : fields.boolean('Fund Raising'),
    }
    def action_cancel(self,cr,uid,ids,conect=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }


    def action_install(self, cr, uid, ids, context=None):
        result=self.read(cr,uid,ids)
        mod_obj = self.pool.get('ir.module.module')
        for res in result:
            for r in res:
                if r<>'id' and res[r]:
                    ids = mod_obj.search(cr, uid, [('name', '=', r)])
                    mod_obj.action_install(cr, uid, ids, context=context)
        cr.commit()
        db, pool = pooler.restart_pool(cr.dbname, update_module=True)
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }


profile_association_config_install_modules_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
