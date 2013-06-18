# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today OpenERP S.A. (<http://openerp.com>).
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


VoteValues = [('-1', 'Not Voted'), ('0', 'Very Bad'), ('25', 'Bad'), \
              ('50', 'Normal'), ('75', 'Good'), ('100', 'Very Good')]
DefaultVoteValue = '50'


class IdeaCategory(osv.Model):
    """ Category of Idea """
    _name = "idea.category"
    _description = "Idea Category"
    _order = 'name asc'

    _columns = {
        'name': fields.char('Category Name', size=64, required=True),
    }

    _sql_constraints = [
        ('name', 'unique(name)', 'The name of the category must be unique')
    ]


class IdeaIdea(osv.Model):
    """ Model of an Idea """
    _name = 'idea.idea'
    _description = 'Propose and Share your Ideas'
    _rec_name = 'name'
    _order = 'name asc'

    def _get_state_list(self, cr, uid, context=None):
        return [('draft', 'New'),
                    ('open', 'Accepted'),
                    ('cancel', 'Refused'),
                    ('close', 'Done')]

    _columns = {
        'create_uid': fields.many2one('res.users', 'Creator', required=True, readonly=True),
        'name': fields.char('Idea Summary', size=64, required=True, readonly=True,
            states={'draft': [('readonly', False)]},
            oldname='title'),
        'description': fields.text('Description', readonly=True,
            states={'draft': [('readonly', False)]},
            help='Content of the idea'),
        'category_ids': fields.many2many('idea.category', string='Tags', readonly=True,
            states={'draft': [('readonly', False)]}),
        'state': fields.selection(_get_state_list, string='Status',
            readonly=True, track_visibility='onchange'),
    }

    _sql_constraints = [
        ('name', 'unique(name)', 'The name of the idea must be unique')
    ]

    _defaults = {
        'state': lambda self, cr, uid, ctx=None: self._get_state_list(cr, uid, ctx)[0][0],
    }

    #------------------------------------------------------
    # Technical stuff
    #------------------------------------------------------

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        """ Override read_group to always display all states. """
        # Default result structure
        states = self._get_state_list(cr, uid, context=context)
        read_group_all_states = [{
                    '__context': {'group_by': groupby[1:]},
                    '__domain': domain + [('state', '=', state_value)],
                    'state': state_value,
                    'state_count': 0,
                } for state_value, state_name in states]
        # Get standard results
        read_group_res = super(IdeaIdea, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby)
        # Update standard results with default results
        result = []
        for state_value, state_name in states:
            res = filter(lambda x: x['state'] == state_value, read_group_res)
            if not res:
                res = filter(lambda x: x['state'] == state_value, read_group_all_states)
            res[0]['state'] = [state_value, state_name]
            result.append(res[0])
        return result

    #------------------------------------------------------
    # Workflow / Actions
    #------------------------------------------------------

    def idea_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def idea_open(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def idea_close(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'close'}, context=context)

    def idea_draft(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)
