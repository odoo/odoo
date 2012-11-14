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

from osv import osv, fields

class event_event(osv.osv):
    _description = 'Portal event'
    _inherit = 'event.event'

    """
    ``visibility``: defines if the event appears on the portal's event page
                    - 'public' means the event will appear for everyone (anonymous)
                    - 'private' means the event won't appear
    """
    _columns = {
        'visibility': fields.selection([('public', 'Public'),('private', 'Private')],
            string='Visibility', help='Event\'s visibility in the portal\'s contact page'),
    }
    _defaults = {
        'visibility': 'private',
    }
