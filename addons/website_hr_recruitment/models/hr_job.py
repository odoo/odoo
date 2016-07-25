# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp.tools.translate import html_translate

class hr_job(osv.osv):
    _name = 'hr.job'
    _inherit = ['hr.job', 'website.seo.metadata', 'website.published.mixin']

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = super(hr_job, self)._website_url(cr, uid, ids, field_name, arg, context=context)
        for job in self.browse(cr, uid, ids, context=context):
            res[job.id] = "/jobs/detail/%s" % job.id
        return res

    def set_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'website_published': False}, context=context)
        return super(hr_job, self).set_open(cr, uid, ids, context)

    _columns = {
        'website_description': fields.html('Website description', translate=html_translate, sanitize=False),
    }
