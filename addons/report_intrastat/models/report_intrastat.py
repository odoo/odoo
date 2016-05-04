# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.sql import drop_view_if_exists
from openerp.addons.decimal_precision import decimal_precision as dp


class res_country(osv.osv):
    _name = 'res.country'
    _inherit = 'res.country'
    _columns = {
        'intrastat': fields.boolean('Intrastat member'),
    }
    _defaults = {
        'intrastat': lambda *a: False,
    }



class report_intrastat_code(osv.osv):
    _name = "report.intrastat.code"
    _description = "Intrastat code"
    _translate = False
    _columns = {
        'name': fields.char('Intrastat Code'),
        'description': fields.char('Description'),
    }



class product_template(osv.osv):
    _name = "product.template"
    _inherit = "product.template"
    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code'),
    }
