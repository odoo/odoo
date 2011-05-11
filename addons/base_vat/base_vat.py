# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2008-2009 B2CK, Cedric Krier, Bertrand Chenal (the methods "check_vat_[a-z]{2}"
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
import string
from osv import osv, fields
from tools.translate import _
import vatnumber     #User should install "python-vatnumber" package from the Synaptic Package Manager to check valid VAT NUMBER

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _split_vat(self, vat):
        vat_country, vat_number = vat[:2].lower(), vat[2:].replace(' ', '')
        return vat_country, vat_number

    def check_vat(self, cr, uid, ids, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            vat_country, vat_number = self._split_vat(partner.vat)
            if not hasattr(vatnumber, 'check_vat_' + vat_country):
                if vat_country.upper() in vatnumber.countries():
                    continue
                return False
            check = getattr(vatnumber, 'check_vat_' + vat_country)
            if not check(vat_number):
                return False
        return True

    def vat_change(self, cr, uid, ids, value, context=None):
        return {'value': {'vat_subjected': bool(value)}}

    _columns = {
        'vat_subjected': fields.boolean('VAT Legal Statement', help="Check this box if the partner is subjected to the VAT. It will be used for the VAT legal statement.")
    }

    def _construct_constraint_msg(self, cr, uid, ids, context=None):
        def default_vat_check(cn, vn):
            return cn[0] in string.ascii_lowercase and cn[1] in string.ascii_lowercase
        vat_country, vat_number = self._split_vat(self.browse(cr, uid, ids)[0].vat)
        if default_vat_check(vat_country, vat_number):
            vat_no = vat_country in vatnumber.countries() and vatnumber.countries() or 'Country Code + Vat Number'
            return _('The Vat does not seems to be correct. You should have entered something like this %s'), (vat_no)
        return _('The VAT is invalid, It should begin with the country code'), ()

    _constraints = [(check_vat, _construct_constraint_msg, ["vat"])]
    
res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
