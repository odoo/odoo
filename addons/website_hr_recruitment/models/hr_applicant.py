# -*- coding: utf-8 -*-

from openerp.osv import osv

class hr_applicant(osv.Model):
    _inherit = 'hr.applicant'

    def website_form_input_filter(self, request, values):
        if 'partner_name' in values:
            values.setdefault('name', '%s\'s Application' % values['partner_name'])
        return values
