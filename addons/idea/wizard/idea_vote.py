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

import wizard
import ir
from mx.DateTime import now
import pooler
import netsvc

vote_form = """<?xml version="1.0" ?>
<form string="Create Tasks">
    <field name="vote"/>
</form>"""

vote_fields = {
      'vote': {'string': 'Post Vote', 'type': 'selection',
        'selection': [('-1','Not Voted'),('0','Very Bad'),('25', 'Bad'),('50','Normal'),('75','Good'),('100','Very Good') ]},
}



class idea_vote(wizard.interface):
    def _do_vote(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        vote_obj = pool.get('idea.vote')
        score=str(data['form']['vote'])
        dic={'idea_id' : data['id'], 'user_id' : uid, 'score' : score }
        vote=vote_obj.create(cr,uid,dic)
        return True

    states = {
        'init':{
            'actions': [],
            'result': {'type':'form', 'arch':vote_form, 'fields':vote_fields, 'state':[('end', 'Cancel'), ('post', 'Post Vote')] },
        },
        'post':{
            'actions': [],
            'result': {'type':'action', 'action': _do_vote, 'state':'end'},
        },
    }
idea_vote('idea.post.vote')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

