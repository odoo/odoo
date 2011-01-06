# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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

from osv import osv

class res_company(osv.osv):
    _inherit = "res.company"
    _description = 'res.company'


    def _get_default_ad(self, addresses):
        city = post_code = address = country_code = ""
        for ads in addresses:
            if ads.type == 'default':
                city = ads.city or ""
                post_code = ads.zip or ""
                if ads.street:
                    address = ads.street or ""
                if ads.street2:
                    address += " " + ads.street2
                if ads.country_id:
                    country_code = ads.country_id and ads.country_id.code or ""
        return city, post_code, address, country_code
res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
