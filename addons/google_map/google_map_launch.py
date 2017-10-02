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
from datetime import timedelta

import pytz

from openerp import models, fields, api, _
from openerp.exceptions import Warning

class launch_map(models.Model):
    _inherit = "res.partner"

    @api.cr_uid_ids_context
    def open_map(self, cr, uid, ids, context=None):
        data = self.browse(cr, uid, ids, context=None)
        url="http://maps.google.com/maps?oi=map&q="
        if data.street:
            url+=data.street.replace(' ','+')
        if data.city:
            url+='+'+data.city.replace(' ','+')
        if data.state_id:
            url+='+'+data.state_id.name.replace(' ','+')
        if data.country_id:
            url+='+'+data.country_id.name.replace(' ','+')
        if data.zip:
            url+='+'+data.zip.replace(' ','+')
        return {'type': 'ir.actions.act_url','target': 'new','url':url,}
