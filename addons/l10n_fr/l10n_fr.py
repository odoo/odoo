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

from openerp.osv import fields, osv

class l10n_fr_report(osv.osv):
    _name = 'l10n.fr.report'
    _description = 'Report for l10n_fr'
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name'),
        'line_ids': fields.one2many('l10n.fr.line', 'report_id', 'Lines', copy=True),
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)','The code report must be unique !')
    ]


class l10n_fr_line(osv.osv):
    _name = 'l10n.fr.line'
    _description = 'Report Lines for l10n_fr'
    _columns = {
        'code': fields.char('Variable Name', size=64),
        'definition': fields.char('Definition'),
        'name': fields.char('Name'),
        'report_id': fields.many2one('l10n.fr.report', 'Report'),
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The variable name must be unique !')
    ]


class res_company(osv.osv):
    _inherit = 'res.company'

    _columns = {
        'siret': fields.char('SIRET', size=14),
        'ape': fields.char('APE'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
