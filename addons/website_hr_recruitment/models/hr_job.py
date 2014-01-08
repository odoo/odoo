# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr_job(osv.osv):
    """ Override to add website-related columns: published, description. """
    _name = 'hr.job'
    _inherit = ['hr.job','website.seo.metadata']

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for job in self.browse(cr, uid, ids, context=context):
            res[job.id] = "%s/job/detail/%s/" % (base_url, job.id)
        return res

    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
        'website_url': fields.function(_website_url, string="Website url", type="char"),
    }
    _defaults = {
        'website_published': False
    }
