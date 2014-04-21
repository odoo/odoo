# -*- coding: utf-8 -*-

import openerp
from openerp.osv import osv, fields

class Documentation(osv.Model):
    _name = 'forum.documentation.toc'
    _description = 'Documentation ToC'
    _inherit = ['website.seo.metadata']
    _order = "parent_left"
    _parent_order = "sequence, name"
    _parent_store = True
    _columns = {
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Name', required=True, translate=True),
        'parent_id': fields.many2one('forum.documentation.toc', 'Parent Table Of Content'),
        'child_ids': fields.one2many('forum.documentation.toc', 'parent_id', 'Children Table Of Content'),
        'parent_left': fields.integer('Left Parent', select=True),
        'parent_right': fields.integer('Right Parent', select=True),
        'post_ids': fields.one2many('forum.post', 'documentation_toc_id', 'Posts'),
    }
    _constraints = [
        (osv.osv._check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]


class DocumentationStage(osv.Model):
    _name = 'forum.documentation.stage'
    _description = 'Post Stage'
    _order = 'sequence'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Stage Name', required=True, translate=True),
    }


class Post(osv.Model):
    _inherit = 'forum.post'
    _columns = {
        'documentation_toc_id': fields.many2one('forum.documentation.toc', 'Documentation ToC'),
        'documentation_stage_id': fields.many2one('forum.documentation.stage', 'Documentation Stage'),
        'color': fields.integer('Color Index')
    }

