# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class hr_applicant(osv.Model):
    _inherit = 'hr.applicant'

    def _get_index_content(self, cr, uid, ids, fields, args, context=None):
        res = dict.fromkeys(ids, '')
        Attachment = self.pool.get('ir.attachment')
        attachment_ids = Attachment.search(cr, uid, [('res_model', '=', 'hr.applicant'), ('res_id', 'in', ids)], context=context)
        for attachment in Attachment.browse(cr, uid, attachment_ids, context=context):
            res[attachment.res_id] += attachment.index_content or ''
        return res

    def _content_search(self, cr, user, obj, name, args, context=None):
        record_ids = set()
        Attachment = self.pool.get('ir.attachment')
        args = ['&'] + args + [('res_model', '=', 'hr.applicant')]
        att_ids = Attachment.search(cr, user, args, context=context)
        record_ids = set(att.res_id for att in Attachment.browse(cr, user, att_ids, context=context))
        return [('id', 'in', list(record_ids))]

    _columns = {
        'index_content': fields.function(
            _get_index_content, fnct_search=_content_search,
            string='Index Content', type="text"),
    }
