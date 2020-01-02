# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID
from odoo.osv import expression


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):
        if self.activity_type_id == self.env.ref('website_sale_referral.mail_act_data_referral_reward'):
            obj = self.env[self.res_model].browse(self.res_id)
            if 'reward_done' in obj:
                obj.reward_done = True
        return super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)


class ReferralAbstract(models.AbstractModel):
    """ Abstract class for objects which can be tracked by referral.
    Contains common behavior for referrals, like checking status, managing rewarding (send email and create activity)
    Models inheriting from this class need to set the following fields in order to work :
    - referred_email
    - referred_name
    - referred_company_name"""
    _name = 'referral.abstract'
    _description = 'Abstract layer for models that want to support referrals'

    STATES_PRIORITY = {'cancel': 0, 'new': 1, 'in_progress': 2, 'done': 3}

    referred_email = fields.Char(string="Referral email", description="The email used to identify the referred")
    referred_name = fields.Char(string="Referral name", description="The name of the referred")
    referred_company_name = fields.Char(string="Referral company", description="The company of the referred")

    deserve_reward = fields.Boolean(description='Is this the first reward to reach the won stage for this referral ?')
    reward_done = fields.Boolean(description='Has the referral been rewarded for this record ?')

    @api.model
    def _get_referrals(self, utm_source_id, referred_email=None):
        objects = self._find_other_referrals(utm_source_id, referred_email)

        result = {}
        for o in objects:
            state = o._get_state_for_referral()
            if o.referred_email and \
               (o.referred_email not in result or self.STATES_PRIORITY[state] > self.STATES_PRIORITY[result[o.referred_email]._get_state_for_referral()]):
                result[o.referred_email] = o

        return result

    @api.model
    def _get_referral_statuses(self, utm_source_id, referred_email=None):
        referrals = self._get_referrals(utm_source_id, referred_email)
        statuses = {k: v._get_state_for_referral() for k, v in referrals.items()}

        if referred_email:
            return statuses.get(referred_email, None)
        else:
            return statuses

    @api.model
    def _get_referral_infos(self, utm_source_id):
        referrals = self._get_referrals(utm_source_id)
        infos = {}
        for k, v in referrals.items():
            infos[k] = {
                'state': v._get_state_for_referral(),
                'name': v.referred_name or '',
                'company': v.referred_company_name or '',
                'iso_date': v.create_date.isoformat(),
            }

        return infos

    def _check_referral_progress(self, old_state, new_state):
        self.ensure_one()
        if new_state == old_state or not self.referred_email:
            return

        others_deserve_reward = self._find_other_referrals(self.source_id, referred_email=self.referred_email, deserve_reward=True)
        if len(others_deserve_reward):
            return

        referral_tracking = self._get_referral_tracking()
        referral_tracking.updates_count += 1
        if new_state == 'done':
            partner = self.env['res.partner'].search([('referral_tracking_id', '=', referral_tracking.id)])
            partner = partner.name if partner else referral_tracking.referrer_email
            template = self.env.ref('website_sale_referral.referral_won_email_template')
            mail_body = template.render({'referred_name': self.referred_name, 'referrer_name': partner}, engine='ir.qweb', minimal_qcontext=True)
            mail = self.env['mail.mail'].sudo().create({
                'subject': 'Referral won !',
                'email_to': referral_tracking.referrer_email,
                'email_from': None,
                'body_html': mail_body,
            })
            mail.send()

            responsible_id = self.env.company.responsible_id or SUPERUSER_ID
            activity = self.activity_schedule(
                act_type_xmlid='website_sale_referral.mail_act_data_referral_reward',
                summary='The referrer for this lead deserves a reward',
                user_id=responsible_id)
            self.deserve_reward = True

    @api.model
    def _find_other_referrals(self, utm_source_id, referred_email=None, deserve_reward=False):
        domain = [
            ('campaign_id', '=', self.env.ref('website_sale_referral.utm_campaign_referral').id),
            ('source_id', '=', utm_source_id.id)]
        if referred_email:
            domain = expression.AND([domain, [('referred_email', '=', referred_email)]])
        if deserve_reward:
            domain = expression.AND([domain, [('deserve_reward', '=', deserve_reward)]])
        return self.search(domain)

    def _get_referral_tracking(self):
        self.ensure_one()
        return self.env['referral.tracking'].search([('utm_source_id', '=', self.source_id.id)], limit=1)
