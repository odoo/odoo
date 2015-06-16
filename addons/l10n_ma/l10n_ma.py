# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class l10n_ma_report(osv.osv):
    _name = 'l10n.ma.report'
    _description = 'Report for l10n_ma_kzc'
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name'),
        'line_ids': fields.one2many('l10n.ma.line', 'report_id', 'Lines', copy=True),
    }
    _sql_constraints = [
                ('code_uniq', 'unique (code)','The code report must be unique !')
        ]

class l10n_ma_line(osv.osv):
    _name = 'l10n.ma.line'
    _description = 'Report Lines for l10n_ma'
    _columns = {
        'code': fields.char('Variable Name', size=64),
        'definition': fields.char('Definition'),
        'name': fields.char('Name'),
        'report_id': fields.many2one('l10n.ma.report', 'Report'),
    }
    _sql_constraints = [
            ('code_uniq', 'unique (code)', 'The variable name must be unique !')
    ]
