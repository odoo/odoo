# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr_job(osv.osv):
    """ Override to add website-related columns: published, description. """
    _inherit = "hr.job"
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
    }

    def _check_address_id_published(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.website_published and obj.address_id and not obj.address_id.website_published:
                return False
        return True
    _constraints = [
        (_check_address_id_published, "This Jobpost can't be published if the field Job Location is not website published.", ['address_id','website_published']),
    ]