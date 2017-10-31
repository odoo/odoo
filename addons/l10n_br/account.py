# -*- encoding: utf-8 -*-

import openerp
from openerp.osv import fields, osv

TAX_DEFAULTS = {
                'base_reduction': 0,
                'amount_mva': 0,
                'amount_type': 'percent',
                }


class account_tax_template(osv.osv):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.template'

    _columns = {
               'tax_discount': fields.boolean('Discount this Tax in Prince', 
                                              help="Mark it for (ICMS, PIS e etc.)."),
               'base_reduction': fields.float('Redution', required=True, 
                                              digits=0,
                                              help="Um percentual decimal em % entre 0-1."),
               'amount_mva': fields.float('MVA Percent', required=True, 
                                          digits=0,
                                          help="Um percentual decimal em % entre 0-1."),
               }
    _defaults = TAX_DEFAULTS

class account_tax(osv.osv):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax'

    _columns = {
               'tax_discount': fields.boolean('Discount this Tax in Prince', 
                                              help="Mark it for (ICMS, PIS e etc.)."),
               'base_reduction': fields.float('Redution', required=True, 
                                              digits=0,
                                              help="Um percentual decimal em % entre 0-1."),
               'amount_mva': fields.float('MVA Percent', required=True, 
                                          digits=0,
                                          help="Um percentual decimal em % entre 0-1."),
               }
    _defaults = TAX_DEFAULTS
