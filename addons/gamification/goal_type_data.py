# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://www.openerp.com>)
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


class gamification_goal_type_data(osv.Model):
    """Goal type data

    Methods for more complex goals not possible with the 'sum' and 'count' mode.
    Each method should return the value that will be set in the 'current' field
    of a user's goal. The return type must be a float or integer.
    """
    _inherit = 'gamification.goal.type'

    def number_following(self, cr, uid, xml_id="mail.thread", context=None):
        """Return the number of 'xml_id' objects the user is following

        The model specified in 'xml_id' must inherit from mail.thread
        """
        ref_obj = self.pool.get(xml_id)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return ref_obj.search(cr, uid, [('message_follower_ids', '=', user.partner_id.id)], count=True, context=context)
