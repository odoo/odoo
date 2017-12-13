# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 Open vision (http://www.openvision.tn).
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

from openerp.osv import fields, osv

class l10n_tn_report(osv.osv):
    _name = 'l10n.tn.report'
    _description = 'Report for l10n_tn'
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name', size=128),
        'line_ids': fields.one2many('l10n.tn.line', 'report_id', 'Lines'),
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)','The code report must be unique !')
    ]

l10n_tn_report()

class l10n_tn_line(osv.osv):
    _name = 'l10n.tn.line'
    _description = 'Report Lines for l10n_tn'
    _columns = {
        'code': fields.char('Variable Name', size=64),
        'definition': fields.char('Definition', size=512),
        'name': fields.char('Name', size=256),
        'report_id': fields.many2one('l10n.tn.report', 'Report'),
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The variable name must be unique !')
    ]

l10n_tn_line()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
