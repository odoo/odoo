# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>).
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

from osv import osv, fields


class mail_star(osv.Model):
    ''' Mail vote feature allow users to select messages and display.
        This allows for example see in one time all important document
        for the user. '''

    _name = 'mail.star'
    _description = 'Mail Star'
    _columns = {
            'message_id': fields.many2one('mail.message', 'Message', select=1,
                ondelete='cascade', required=True),
            'user_id': fields.many2one('res.users', 'User', select=1,
                ondelete='cascade', required=True),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
