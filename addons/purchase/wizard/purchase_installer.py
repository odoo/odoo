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
from osv import fields, osv

class purchase_config_wizard(osv.osv_memory):
    _name = 'purchase.config.wizard'

    _columns = {
        'default_method' : fields.selection(
            [('manual', 'Based on Purchase Orders'),
             ('picking', 'Based on Receptions'),
             ('order', 'Pre-Generate Draft Invoices on Purchase Orders'),
            ],
            'Default Invoicing Control Method',
            required=True,
        ),
    }

    def validate_cb(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids, context=context)[0]

        proxy = self.pool.get('ir.values')
        proxy.set(cr, uid, 'default', False, 'invoice_method', ['purchase.order'], wizard.default_method),

        return {'type' : 'ir.actions.act_window_close'}

purchase_config_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
