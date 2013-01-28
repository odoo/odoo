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
from openerp.osv import fields,osv

class account_invoice_report(osv.osv):
    _inherit = 'account.invoice.report'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

    def _select(self):
        return  super(account_invoice_report, self)._select() + ", sub.section_id as section_id"

    def _sub_select(self):
        return  super(account_invoice_report, self)._sub_select() + ", ai.section_id as section_id"

    def _group_by(self):
        return super(account_invoice_report, self)._group_by() + ", ai.section_id"

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
