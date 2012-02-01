# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2011 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import tools
from osv import osv
from osv import fields
from tools.translate import _

class mail_subscription(osv.osv):
    """
    mail_subscription holds the data related to the follow mechanism inside OpenERP.
    A subscription can be of following:
    - res_model: model of the followed objects
    - res_id: ID of resource OR
    - res_domain: a domain filtering followed objects
    """
    
    _name = 'mail.subscription'
    _rec_name = 'id'
    _columns = {
        'res_model': fields.char('Related Document model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'res_domain': fields.char('res_domain', size=256),
        'user_id': fields.integer('Related User ID', select=1),
    }
    
    _defaults = {
    }

mail_subscription()
