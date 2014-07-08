# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

class hr_job(osv.osv):
    _name = 'hr.job'
    _inherit = ['hr.job','website.seo.metadata']

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        for job in self.browse(cr, uid, ids, context=context):
            res[job.id] = "/jobs/detail/%s" % job.id
        return res

    def job_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'website_published': False}, context=context)
        return super(hr_job, self).job_open(cr, uid, ids, context)

    _columns = {
        'website_published': fields.boolean('Published', copy=False),
        'website_description': fields.html('Website description'),
        'website_url': fields.function(_website_url, string="Website URL", type="char"),
    }
    _defaults = {
        'website_published': False
    }
