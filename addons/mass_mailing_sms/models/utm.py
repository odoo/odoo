# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    mailing_sms_ids = fields.One2many(
        'mailing.mailing', 'campaign_id',
        domain=[('mailing_type', '=', 'sms')],
        string='Mass SMS',
        groups="mass_mailing.group_mass_mailing_user")
    mailing_sms_count = fields.Integer('Number of Mass SMS',
        compute="_compute_mailing_sms_count",
        groups="mass_mailing.group_mass_mailing_user")

    # A/B Testing
    ab_testing_mailings_sms_count = fields.Integer("A/B Test Mailings SMS #", compute="_compute_mailing_sms_count")
    ab_testing_sms_winner_selection = fields.Selection([
        ('manual', 'Manual'),
        ('clicks_ratio', 'Highest Click Rate')], string="SMS Winner Selection", default="clicks_ratio")

    @api.depends('mailing_mail_ids', 'mailing_sms_ids')
    def _compute_ab_testing_total_pc(self):
        super()._compute_ab_testing_total_pc()
        for campaign in self:
            campaign.ab_testing_total_pc += sum([
                mailing.ab_testing_pc for mailing in campaign.mailing_sms_ids.filtered('ab_testing_enabled')
            ])

    @api.depends('mailing_sms_ids')
    def _compute_mailing_sms_count(self):
        if self.ids:
            mailing_sms_data = self.env['mailing.mailing'].read_group(
                [('campaign_id', 'in', self.ids), ('mailing_type', '=', 'sms')],
                ['campaign_id', 'ab_testing_enabled'],
                ['campaign_id', 'ab_testing_enabled'],
                lazy=False,
            )
            ab_testing_mapped_sms_data = {}
            mapped_sms_data = {}
            for data in mailing_sms_data:
                if data['ab_testing_enabled']:
                    ab_testing_mapped_sms_data.setdefault(data['campaign_id'][0], []).append(data['__count'])
                mapped_sms_data.setdefault(data['campaign_id'][0], []).append(data['__count'])
        else:
            mapped_sms_data = dict()
            ab_testing_mapped_sms_data = dict()
        for campaign in self:
            campaign.mailing_sms_count = sum(mapped_sms_data.get(campaign._origin.id or campaign.id, []))
            campaign.ab_testing_mailings_sms_count = sum(ab_testing_mapped_sms_data.get(campaign._origin.id or campaign.id, []))

    def action_create_mass_sms(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.action_create_mass_mailings_from_campaign")
        action['context'] = {
            'default_campaign_id': self.id,
            'default_mailing_type': 'sms',
            'search_default_assigned_to_me': 1,
            'search_default_campaign_id': self.id,
            'default_user_id': self.env.user.id,
        }
        return action

    def action_redirect_to_mailing_sms(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing_sms.mailing_mailing_action_sms")
        action['context'] = {
            'default_campaign_id': self.id,
            'default_mailing_type': 'sms',
            'search_default_assigned_to_me': 1,
            'search_default_campaign_id': self.id,
            'default_user_id': self.env.user.id,
        }
        action['domain'] = [('mailing_type', '=', 'sms')]
        return action

    @api.model
    def _cron_process_mass_mailing_ab_testing(self):
        ab_testing_campaign = super()._cron_process_mass_mailing_ab_testing()
        for campaign in ab_testing_campaign:
            ab_testing_mailings = campaign.mailing_sms_ids.filtered(lambda m: m.ab_testing_enabled)
            if not ab_testing_mailings.filtered(lambda m: m.state == 'done'):
                continue
            ab_testing_mailings.action_send_winner_mailing()
        return ab_testing_campaign


class UtmMedium(models.Model):
    _inherit = 'utm.medium'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_utm_medium_sms(self):
        utm_medium_sms = self.env.ref('mass_mailing_sms.utm_medium_sms', raise_if_not_found=False)
        if utm_medium_sms and utm_medium_sms in self:
            raise UserError(_(
                "The UTM medium '%s' cannot be deleted as it is used in some main "
                "functional flows, such as the SMS Marketing.",
                utm_medium_sms.name
            ))
