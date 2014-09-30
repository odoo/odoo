# -*- encoding: utf-8 -*-
##############################################################################
#
#    Asterisk click2dial module for OpenERP
#    Copyright (C) 2014 Alexis de Lattre (alexis@via.ecp.fr)
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

import openerp


class BasePhoneController(openerp.addons.web.http.Controller):
    _cp_path = '/base_phone'

    @openerp.addons.web.http.jsonrequest
    def click2dial(self, req, phone_number, click2dial_model, click2dial_id):
        res = req.session.model('phone.common').click2dial(
            phone_number, {
                'click2dial_model': click2dial_model,
                'click2dial_id': click2dial_id,
                })
        return res
