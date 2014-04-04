# -*- coding: utf-8 -*-

from openerp.osv import osv


class MassMailing(osv.Model):
    """Inherit to add hr.applicant objects available for mass mailing """
    _name = 'mail.mass_mailing'
    _inherit = 'mail.mass_mailing'

    def _get_mailing_model(self, cr, uid, context=None):
        res = super(MassMailing, self)._get_mailing_model(cr, uid, context=context)
        res.append(('hr.applicant', 'Applicants'))
        return res

    def _get_model_to_list_action_id(self, cr, uid, model, context=None):
        if model == 'hr.applicant':
            return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing_applicant.action_applicant_to_mailing_list')
        else:
            return super(MassMailing, self)._get_model_to_list_action_id(cr, uid, model, context=context)

    def get_recipients_data(self, cr, uid, mailing, res_ids, context=None):
        if mailing.mailing_model == 'hr.applicant':
            res = {}
            for applicant in self.pool['hr.applicant'].browse(cr, uid, res_ids, context=context):
                if applicant.partner_id:
                    res[applicant.id] = {'partner_id': applicant.partner_id.id, 'name': applicant.partner_id.name, 'email': applicant.partner_id.email}
                else:
                    name, email = self.pool['res.partner']._parse_partner_name(applicant.email_from, context=context)
                    res[applicant.id] = {'partner_id': False, 'name': name or email, 'email': email}
            return res
        return super(MassMailing, self).get_recipients_data(cr, uid, mailing, res_ids, context=context)
