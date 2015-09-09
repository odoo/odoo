# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class Post(osv.Model):
    _inherit = 'forum.post'

    _columns = {
        'documentation_toc_id': fields.many2one('forum.documentation.toc', 'Documentation ToC', ondelete='set null'),
        'documentation_stage_id': fields.many2one('forum.documentation.stage', 'Documentation Stage'),
        'color': fields.integer('Color Index')
    }

    def _get_default_stage_id(self, cr, uid, context=None):
        stage_ids = self.pool["forum.documentation.stage"].search(cr, uid, [], limit=1, context=context)
        return stage_ids and stage_ids[0] or False

    _defaults = {
        'documentation_stage_id': _get_default_stage_id,
    }

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        stage_obj = self.pool.get('forum.documentation.stage')
        stage_ids = stage_obj.search(cr, uid, [], context=context)
        result = stage_obj.name_get(cr, uid, stage_ids, context=context)
        return result, {}

    _group_by_full = {
        'documentation_stage_id': _read_group_stage_ids,
    }
