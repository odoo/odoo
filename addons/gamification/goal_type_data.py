# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv
from openerp import SUPERUSER_ID

from datetime import date
from dateutil.relativedelta import relativedelta


class gamification_goal_type_data(osv.Model):
    """Goal type data

    Methods for more complex goals not possible with the 'sum' and 'count' mode.
    Each method should return the value that will be set in the 'current' field
    of a user's goal. The return type must be a float or integer.
    """
    _inherit = 'gamification.goal.type'

    def last_connection(self, cr, uid, context=None):
        """Return the number of days since the last connection"""
        if context is None: context = {}
        user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        delta = date.today() - user.login_date
        return delta.days

    def months_since_created(self, cr, uid, context=None):
        """Return the number of months since the user was created"""
        if context is None: context = {}
        user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        today = date.today()
        delta = relativedelta(years=user.create_date.year - today.year, months=user.create_date.month - today.month)
        return delta.years*12 + delta.months

    def number_following(self, cr, uid, xml_id="mail.thread", context=None):
        """Return the number of 'xml_id' objects the user is following

        'message_is_follower' is a non-stored field so could not be in a search
        domain with a 'count' goal type
        The object must inherit from mail.thread
        """
        if context is None: context = {}
        ref_obj = self.pool.get(xml_id)
        obj_ids = ref_obj.search(cr, uid, [], context=context)
        following_count = 0
        for obj in ref_obj.browse(cr, uid, obj_ids, context=context):
            if obj.message_is_follower:
                following_count += 1
        return following_count
