# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import orm
from osv import fields

class transient_update_maildomain(orm.TransientModel):
    
    _name = "transient.update.maildomain"
    _description = "Update Mail Domain"
    _columns = {
        'name' : fields.text('Domain', required=True),
    }
    def update_domain(self, cr, uid, ids, context=None):
        config_parameter_pool = self.pool.get("ir.config_parameter")
        for record in self.browse(cr, uid, ids, context):
            config_parameter_pool.set_param(cr, uid, "mail.catchall.domain", record.name, context)
        return {'type': 'ir.actions.act_window_close'}
