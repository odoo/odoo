# -*- encoding: utf-8 -*-
##############################################################################
#
#     Author: Tatár Attila <atta@nvm.ro>
#    Copyright (C) 2011-2014 TOTAL PC SYSTEMS (http://www.erpsystems.ro). 
#    Copyright (C) 2014 Tatár Attila
#     Based on precedent versions developed by Fil System, Mihai Fekete
#     
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv
from openerp.tools.translate import _

class res_partner(osv.Model):
    """ Extending partner object """
    
    _name = "res.partner"
    _inherit = "res.partner"
    
    def _cnpenable(self,cr, uid, ids, fname, args, context=None):
        res = {}
        cnp_status = self.pool.get("ir.config_parameter").get_param(
            cr, uid, "cnp_identify", context=context)
        for i in ids:
            res[i] = cnp_status
        return res
    
    def get_partn_type(self,cr, uid, ids, fname, args, context=None):
        res = {} 
        for i in ids:
            if self.read(cr, uid, i, ['is_company'])['is_company']:
                res[i] = 'partner'
            else:
                res[i] = 'contact'  
        return res
    
    _columns = {
        'nrc' : fields.char('NRC',
                  help=_('Registration number at the Registry of Commerce')),
        'vat': fields.char('TIN',  help="Tax Identification Number."),
        'skip_verify': fields.boolean('Skip TIN verification',
                         help=_('Check to skip formal verification for TIN'
                                ' field eg.without RO attribute')),
        'id_nr':fields.char('ID Nr'),
        'id_issued_by':fields.char('ID Issued by'),
        'cnp':fields.char('CNP'),        
        'cnp_enable': fields.function(_cnpenable, type='boolean'),
        'partn_title_type':fields.function(get_partn_type, type='char'),
    }

    # The SQL constraint is present only to display the right error message to the
    # user when the partial unique index defined below raise errors  
    # The real constraint need to be implemented with PARTIAL UNIQUE INDEXES (see auto_init),
    # due to the way accounting data is delegated by contacts to their companies from Odoo V7.0.
    _sql_constraints = [
       ('vat_uniq', 'unique (id)', 'The TIN of the partner must be unique !'),       
    ]
    
    def check_vat(self, cr, uid, ids, context=None):
        """ Formal verification of VAT code """        
        to_check_ids = []
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue             
            elif partner.vat and partner.skip_verify:
                continue
            else:
                to_check_ids.append(partner.id)        
        res = super(res_partner,self).check_vat(cr, uid, to_check_ids, context=context)
        if not res:
            return False        
        return True

    _constraints = [(check_vat, _("Invalid TIN!"), ["vat"])]

    def _auto_init(self, cr, context=None):
        result = super(res_partner, self)._auto_init(cr, context=context)
        # Real implementation of the vat/nrc constraints: only "commercial entities" need to have
        # unique numbers, and the condition for being a commercial entity is "is_company".
        # Contacts inside a company automatically have a copy of the company's commercial fields
        # (see _commercial_fields()), so they are automatically consistent.
        cr.execute("""
            DROP INDEX IF EXISTS res_partner_vat_uniq_for_companies;
            DROP INDEX IF EXISTS res_partner_nrc_uniq_for_companies;
            CREATE UNIQUE INDEX res_partner_vat_uniq_for_companies 
                ON res_partner (vat) WHERE is_company;
        """)
        return result

    def _commercial_fields(self, cr, uid, context=None):        
        res = super(res_partner, self)._commercial_fields(cr, uid, 
                                                          context=context)
        return res + ['skip_verify','nrc']
