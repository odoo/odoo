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

from osv import fields, osv
from tools.translate import _

class idea_post_vote(osv.osv_memory):
    """ Post Vote For Idea """

    _name = "idea.post.vote"
    _description = "Post vote"

    _columns = {
                'vote': fields.selection([('-1', 'Not Voted'),
                                          ('0', 'Very Bad'),
                                          ('25', 'Bad'),
                                          ('50', 'Normal'),
                                          ('75', 'Good'),
                                          ('100', 'Very Good') ], 'Give Vote', required=True),
                'content': fields.text('Comment'),
                }
    
    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        """
        idea_obj = self.pool.get('idea.idea')
        for idea in idea_obj.browse(cr, uid, context.get('active_ids', [])):
            
            for active_id in context.get('active_ids'):
                cr.execute('select count(id) from idea_vote where user_id=%s\
                                                      and idea_id=%s' % (uid, active_id))
                res = cr.fetchone()[0]
                user_limit = idea.vote_limit
                if  res >= user_limit:
                   raise osv.except_osv(_('Warning !'),_("You can not give Vote for this idea more than %s times") % (user_limit))
        
            if idea.state != 'open':
                raise osv.except_osv(_('Warning !'), _('Idea should be in \
\'Open\' state before vote for that idea.'))
        return False

    def do_vote(self, cr, uid, ids, context=None):

        """
        Create idea vote.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Idea Post vote’s IDs.
        @return: Dictionary {}
        """
        data = context and context.get('active_ids', []) or []
        vote_obj = self.pool.get('idea.vote')
        for do_vote_obj in self.read(cr, uid, ids):
            score = str(do_vote_obj['vote'])
            comment = do_vote_obj['content']
            for id in data:
                dic = {'idea_id': id, 'user_id': uid, 'score': score, 'comment': comment}
                vote = vote_obj.create(cr, uid, dic)
            return {}
        
idea_post_vote()

class idea_select(osv.osv_memory):
    
    """ Select idea for vote."""
    
    _name = "idea.select"
    _description = "select idea"

    _columns = {
                'idea_id': fields.many2one('idea.idea', 'Idea', required=True),
               }
               
    def open_vote(self, cr, uid, ids, context=None):
       """ 
       This function load column.
       @param cr: the current row, from the database cursor,
       @param uid: the current users ID for security checks,
       @param ids: List of load column,
       @return: dictionary of query logs clear message window
       """
       idea_obj = self.browse(cr, uid, ids)
       for idea in idea_obj:
           idea_id = idea.idea_id.id
          
       data_obj = self.pool.get('ir.model.data')
       id2 = data_obj._get_id(cr, uid, 'idea', 'view_idea_post_vote')
       if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
       value = {
            'view_type': 'form', 
            'view_mode': 'form', 
            'res_model': 'idea.post.vote', 
            'views': [(id2, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')], 
            'type': 'ir.actions.act_window', 
            'target': 'new',
            'context': {'active_ids': [idea_id]}
       }
       return value
    
idea_select()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
