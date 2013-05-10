
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2012 (<http://www.erpsystems.ro>). All Rights Reserved
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

class res_partner(osv.osv):
    _name = "res.partner"
    _inherit = "res.partner"
    _columns = {
        'nrc' : fields.char('NRC', size=16, help='Registration number at the Registry of Commerce'),
    }

    # The SQL constraints are no-ops but present only to display the right error message to the
    # user when the partial unique indexes defined below raise errors/  
    # The real constraints need to be implemented with PARTIAL UNIQUE INDEXES (see auto_init),
    # due to the way accounting data is delegated by contacts to their companies in OpenERP 7.0.
    _sql_constraints = [
       ('vat_uniq', 'unique (id)', 'The vat of the partner must be unique !'),
       ('nrc_uniq', 'unique (id)', 'The code of the partner must be unique !')
    ]

    def _auto_init(self, cr, context=None):
        result = super(res_partner, self)._auto_init(cr, context=context)
        # Real implementation of the vat/nrc constraints: only "commercial entities" need to have
        # unique numbers, and the condition for being a commercial entity is "is_company or parent_id IS NULL".
        # Contacts inside a company automatically have a copy of the company's commercial fields
        # (see _commercial_fields()), so they are automatically consistent.
        cr.execute("""
            DROP INDEX IF EXISTS res_partner_vat_uniq_for_companies;
            DROP INDEX IF EXISTS res_partner_nrc_uniq_for_companies;
            CREATE UNIQUE INDEX res_partner_vat_uniq_for_companies ON res_partner (vat) WHERE is_company OR parent_id IS NULL;
            CREATE UNIQUE INDEX res_partner_nrc_uniq_for_companies ON res_partner (nrc) WHERE is_company OR parent_id IS NULL;
        """)
        return result

    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + ['nrc']

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
