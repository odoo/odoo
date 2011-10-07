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
              ('100', 'Very Good') ],
        'Post Vote', required=True),
        'note': fields.text('Description'),
    }

    def get_default(self, cr, uid, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
        idea_obj = self.pool.get('idea.idea')

        if context.get('active_id'):
            idea = idea_obj.browse(cr, uid, context.get('active_id'), context=context)
            return idea.my_vote
        else:
            return 75

    _defaults = {
        'vote': get_default,
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
        vote_obj = self.pool.get('idea.vote')
        
        ctx_key = 'idea_ids' if context.get('idea_ids') is not None else 'active_ids'

        for idea in idea_obj.browse(cr, uid, context.get(ctx_key, []), context=context):

            for idea_id in context.get(ctx_key):

                vote_ids = vote_obj.search(cr, uid, [('user_id', '=', uid), ('idea_id', '=', idea_id)])
                vote_obj_id = vote_obj.browse(cr, uid, vote_ids)
                count = 0
                for vote in vote_obj_id:
                    count += 1

                user_limit = idea.vote_limit
                if  count >= user_limit:
                   raise osv.except_osv(_('Warning !'),_("You can not give Vote for this idea more than %s times") % (user_limit))

            if idea.state != 'open':
                raise osv.except_osv(_('Warning !'), _('Idea must be in \
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

        vote_ids = context and context.get('active_ids', []) or []
        vote_id = context['active_ids'][0]
        vote_pool = self.pool.get('idea.vote')
        idea_pool = self.pool.get('idea.idea')
        comment_pool = self.pool.get('idea.comment')

        for do_vote_obj in self.read(cr, uid, ids, context=context):
            score = str(do_vote_obj['vote'])
            comment = do_vote_obj.get('note', False)
            vote = {
                'idea_id': vote_id,
                'user_id': uid,
                'score': score
            }
            if comment:
                comment = {
                    'user_id':uid,
                    'idea_id':vote_id,
                    'content': comment,
                }
                comment = comment_pool.create(cr, uid, comment)

            idea_pool._vote_save(cr, uid, vote_id, None, score, context)
            #vote = vote_pool.create(cr, uid, vote)
            return {'type': 'ir.actions.act_window_close'}

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
       if context is None:
            context = {}
       idea_obj = self.browse(cr, uid, ids, context=context)
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
            'context': {'idea_ids': [idea_id]}
       }
       return value

idea_select()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
