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

import openerp.addons.web_im.im as im
import json
from osv import osv, fields

class live_support_channel(osv.osv):
    _name = 'live_support.channel'
    _columns = {
        'name': fields.char(string="Name", size=200, required=True),
        'user_ids': fields.many2many('im.user', 'live_support_channel_im_user', 'channel_id', 'user_id', string="Users"),
    }

class im_user(osv.osv):
    _inherit = 'im.user'
    _columns = {
        'support_channel_ids': fields.many2many('live_support.channel', 'live_support_channel_im_user', 'user_id', 'channel_id', string="Support Channels"),
    }
