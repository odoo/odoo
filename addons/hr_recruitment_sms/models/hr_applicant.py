# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    def action_send_sms(self):
        res = self.env['ir.actions.act_window']._for_xml_id('sms.sms_composer_action_form')
        res['context'] = {
            'default_composition_mode': 'mass',
            'default_mass_keep_log': True,
            'default_res_ids': self.ids,
        }
        return res
