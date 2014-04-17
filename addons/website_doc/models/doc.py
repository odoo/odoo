# -*- coding: utf-8 -*-

import openerp
from openerp.osv import osv, fields
from openerp.tools.translate import _


class Documentation(osv.Model):
    _name = 'documentation.toc'
    _description = 'Table Of Content For Documentation'
    _inherit = ['website.seo.metadata']

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'parent_id': fields.many2one('documentation.toc', 'Parent Table Of Content'),
        'child_ids': fields.one2many('documentation.toc', 'parent_id', 'Children Table Of Content'),
        'post_ids': fields.one2many('forum.post', 'toc_id', 'Posts'),
    }

class Post(osv.Model):
    _inherit = 'forum.post'

    def _get_pertinent_answer(self, cr, uid, ids, field_name=False, arg={}, context=None):
        '''Set answer which have been accepted or have maximum votes'''
        res = {}
        for post in self.browse(cr, uid, ids, context=context):
            pertinent_answer_ids = self.search(cr, uid, [('parent_id', '=', post.id)], order='is_correct, vote_count desc', context=context)
            res[post.id] = pertinent_answer_ids[0] if pertinent_answer_ids else False
        return res

    _columns = {
        'name': fields.char('Title', size=128),
        'toc_id': fields.many2one('documentation.toc', 'Table of Content'),
        'pertinent_answer_id':fields.function(_get_pertinent_answer, string="Pertinent Answer", type='many2one', relation="forum.post",
            store={
                'forum.post': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            }
        ),
    }
