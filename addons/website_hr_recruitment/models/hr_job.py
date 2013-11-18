# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr_job(osv.osv):
    """ Override to add website-related columns: published, description. """
    _inherit = "hr.job"
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
    }
    _defaults = {
        'website_published': False
    }
