# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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

from osv import fields, osv

class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'ref_companies': fields.one2many('res.company', 'partner_id',
        'Companies that refers to partner'),
    }

res_partner()

class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"
    _columns = {
        'name': fields.char('Description', size=128, required=True),
        'post_number': fields.char('Post number', size=64),
        'bvr_adherent_num': fields.char('BVR adherent number', size=11),
        'dta_code': fields.char('DTA code', size=5),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        bank_type_obj = self.pool.get('res.partner.bank.type')

        type_ids = bank_type_obj.search(cr, uid, [])
        bank_type_names = {}
        for bank_type in bank_type_obj.browse(cr, uid, type_ids,
                context=context):
            bank_type_names[bank_type.code] = bank_type.name
        res = []
        for r in self.read(cr, uid, ids, ['name','state'], context):
            res.append((r['id'], r['name']+' : '+bank_type_names[r['state']]))
        return res

    _sql_constraints = [
        ('bvr_adherent_uniq', 'unique (bvr_adherent_num)', 'The BVR adherent number must be unique !')
    ]

res_partner_bank()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: