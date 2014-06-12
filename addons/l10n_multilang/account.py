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
from openerp.tools.translate import _


#in this file, we mostly add the tag translate=True on existing fields that we now want to be translated

class account_account_template(osv.osv):
    _inherit = 'account.account.template'
    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True, translate=True),
    }

class account_account(osv.osv):
    _inherit = 'account.account'
    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True, translate=True),
    }

class account_tax(osv.osv):
    _inherit = 'account.tax'
    _columns = {
        'name': fields.char('Tax Name', size=128, required=True, select=True, translate=True),
    }


class account_tax_template(osv.osv):
    _inherit = 'account.tax.template'
    _columns = {
        'name': fields.char('Tax Name', size=128, required=True, select=True, translate=True),
    }


class account_tax_code_template(osv.osv):
    _inherit = 'account.tax.code.template'
    _columns = {
        'name': fields.char('Tax Case Name', size=64, required=True, translate=True),
    }


class account_chart_template(osv.osv):
    _inherit = 'account.chart.template'
    _columns={
        'name': fields.char('Name', size=64, required=True, translate=True),
        'spoken_languages': fields.char('Spoken Languages', size=64, help="State here the languages for which the translations of templates could be loaded at the time of installation of this localization module and copied in the final object when generating them from templates. You must provide the language codes separated by ';'"),
    }
    _order = 'name'


class account_fiscal_position(osv.osv):
    _inherit = 'account.fiscal.position'
    _columns = {
        'name': fields.char('Fiscal Position', size=64, required=True, translate=True),
        'note': fields.text('Notes', translate=True),
    }


class account_fiscal_position_template(osv.osv):
    _inherit = 'account.fiscal.position.template'
    _columns = {
        'name': fields.char('Fiscal Position Template', size=64, required=True, translate=True),
        'note': fields.text('Notes', translate=True),
    }


class account_journal(osv.osv):
    _inherit = 'account.journal'
    _columns = {
        'name': fields.char('Journal Name', size=64, required=True, translate=True),
    }


class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'
    _columns = {
        'name': fields.char('Account Name', size=128, required=True, translate=True),
    }


class account_analytic_journal(osv.osv):
    _inherit = 'account.analytic.journal'
    _columns = {
        'name': fields.char('Journal Name', size=64, required=True, translate=True),
    }
