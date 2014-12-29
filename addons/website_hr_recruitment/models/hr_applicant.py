# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.tools.translate import _

class hr_applicant(osv.Model):
    _inherit = 'hr.applicant'

    def website_form_input_filter(self, data):
        data['post']['name'] = data['post']['partner_name'] + _('s Application')
        return data