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

from openerp.osv import fields, osv


class mail_vote(osv.Model):
    ''' Mail vote feature allow users to like and unlike messages attached
        to a document. This allows for example to build a ranking-based
        displaying of messages, for FAQ. '''

    _name = 'mail.vote'
    _description = 'Mail Vote'
    _columns = {
            'message_id': fields.many2one('mail.message', 'Message', select=1,
                ondelete='cascade', required=True),
            'user_id': fields.many2one('res.users', 'User', select=1,
                ondelete='cascade', required=True),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
