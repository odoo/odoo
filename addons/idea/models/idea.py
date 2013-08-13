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
                    ('open', 'In discussion'),
                    ('close', 'Accepted'),
                    ('cancel', 'Refused')]

    def _get_color(self, cr, uid, ids, fields, args, context=None):
        res = dict.fromkeys(ids, 3)
        for idea in self.browse(cr, uid, ids, context=context):
            if idea.priority == 'low':
                res[idea.id] = 0
            elif idea.priority == 'high':
                res[idea.id] = 7
        return res

    _columns = {
        'user_id': fields.many2one('res.users', 'Responsible', required=True),
        'name': fields.char('Summary', required=True, readonly=True,
            states={'draft': [('readonly', False)]},
            oldname='title'),
        'description': fields.text('Description', required=True,
            states={'draft': [('readonly', False)]},
            help='Content of the idea'),
        'category_ids': fields.many2many('idea.category', string='Tags'),
        'state': fields.selection(_get_state_list, string='Status', required=True),
        'priority': fields.selection([('low', 'Low'), ('normal', 'Normal'), ('high', 'High')],
            string='Priority', required=True),
        'color': fields.function(_get_color, type='integer', string='Color Index'),
    }

    _sql_constraints = [
        ('name', 'unique(name)', 'The name of the idea must be unique')
    ]

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: uid,
        'state': lambda self, cr, uid, ctx=None: self._get_state_list(cr, uid, ctx)[0][0],
        'priority': 'normal',
    }

    #------------------------------------------------------
    # Technical stuff
    #------------------------------------------------------

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
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
        else:
            return super(IdeaIdea, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)

    #------------------------------------------------------
    # Workflow / Actions
    #------------------------------------------------------

    def idea_set_low_priority(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'priority': 'low'}, context=context)

    def idea_set_normal_priority(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'priority': 'normal'}, context=context)

    def idea_set_high_priority(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'priority': 'high'}, context=context)
