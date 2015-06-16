# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
