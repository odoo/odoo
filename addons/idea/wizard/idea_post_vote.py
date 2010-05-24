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
    
    def get_default(self, cr, uid, context={}):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        """
        idea_obj = self.pool.get('idea.idea')
        
        if context.get('active_id'):
            idea = idea_obj.browse(cr, uid, context.get('active_id'))
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

        for idea in idea_obj.browse(cr, uid, context.get('active_ids', [])):
            if idea.state in ['draft', 'close', 'cancel']:
                raise osv.except_osv(_("Warning !"), _("Draft/Accepted/Cancelled ideas Could not be voted"))
            if idea.state != 'open':
                raise osv.except_osv(_('Warning !'), _('idea should be in \'Open\' state before vote for that idea.'))
        return False

    def do_vote(self, cr, uid, ids, context):
        """
        Create idea vote.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Idea Post vote’s IDs.
        @return: Dictionary {}
        """
        
        vote_id = context and context.get('active_id', False) or False
        vote_pool = self.pool.get('idea.vote')
        comment_pool = self.pool.get('idea.comment')

        for do_vote_obj in self.read(cr, uid, ids):
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
                
            vote = vote_pool.create(cr, uid, vote)
            return {}

idea_post_vote()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

