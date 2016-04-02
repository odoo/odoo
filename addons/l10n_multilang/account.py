# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp.osv import fields, osv
from openerp.tools.translate import _


#in this file, we mostly add the tag translate=True on existing fields that we now want to be translated

class account_account_template(osv.osv):
    _inherit = 'account.account.template'
    _columns = {
        'name': fields.char('Name', required=True, select=True, translate=True),
    }

class account_account(osv.osv):
    _inherit = 'account.account'
    _columns = {
        'name': fields.char('Name', required=True, select=True, translate=True),
    }

class account_tax(osv.osv):
    _inherit = 'account.tax'
    _columns = {
        'name': fields.char('Tax Name', required=True, select=True, translate=True),
    }


class account_tax_template(osv.osv):
    _inherit = 'account.tax.template'
    _columns = {
        'name': fields.char('Tax Name', required=True, select=True, translate=True),
    }


class account_chart_template(osv.osv):
    _inherit = 'account.chart.template'
    _columns={
        'name': fields.char('Name', required=True, translate=True),
        'spoken_languages': fields.char('Spoken Languages', help="State here the languages for which the translations of templates could be loaded at the time of installation of this localization module and copied in the final object when generating them from templates. You must provide the language codes separated by ';'"),
    }
    _order = 'name'


class account_fiscal_position(osv.osv):
    _inherit = 'account.fiscal.position'
    _columns = {
        'name': fields.char('Fiscal Position', required=True, translate=True),
        'note': fields.text('Notes', translate=True),
    }


class account_fiscal_position_template(osv.osv):
    _inherit = 'account.fiscal.position.template'
    _columns = {
        'name': fields.char('Fiscal Position Template', required=True, translate=True),
        'note': fields.text('Notes', translate=True),
    }


class account_journal(osv.osv):
    _inherit = 'account.journal'
    _columns = {
        'name': fields.char('Journal Name', required=True, translate=True),
    }


class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'
    _columns = {
        'name': fields.char('Account Name', required=True, translate=True),
    }

