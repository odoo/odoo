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

from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
import time

VoteValues = [('-1', 'Not Voted'), ('0', 'Very Bad'), ('25', 'Bad'), \
              ('50', 'Normal'), ('75', 'Good'), ('100', 'Very Good') ]
DefaultVoteValue = '50'

class idea_category(osv.osv):
    """ Category of Idea """
    _name = "idea.category"
    _description = "Idea Category"
    _columns = {
        'name': fields.char('Category Name', size=64, required=True),
    }
    _sql_constraints = [
        ('name', 'unique(name)', 'The name of the category must be unique')
    ]
    _order = 'name asc'


class idea_idea(osv.osv):
    """ Idea """
    _name = 'idea.idea'
    _inherit = ['mail.thread']
    _columns = {
        'create_uid': fields.many2one('res.users', 'Creator', required=True, readonly=True),
        'name': fields.char('Idea Summary', size=64, required=True, readonly=True, oldname='title', states={'draft': [('readonly', False)]}),
        'description': fields.text('Description', help='Content of the idea', readonly=True, states={'draft': [('readonly', False)]}),
        'category_ids': fields.many2many('idea.category', string='Tags', readonly=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection([('draft', 'New'),
            ('open', 'Accepted'),
            ('cancel', 'Refused'),
            ('close', 'Done')],
            'Status', readonly=True, track_visibility='onchange',
        )
    }
    _sql_constraints = [
        ('name', 'unique(name)', 'The name of the idea must be unique')
    ]
    _defaults = {
        'state': lambda *a: 'draft',
    }
    _order = 'name asc'

    def idea_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def idea_open(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def idea_close(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'close'}, context=context)

    def idea_draft(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)
