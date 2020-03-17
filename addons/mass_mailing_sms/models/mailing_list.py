# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class MailingList(models.Model):
    _inherit = 'mailing.list'

    contact_ids_valid_sms = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        compute='_compute_statistic', string='Valid sms contacts'
    )
    contact_valid_sms_count = fields.Integer(compute='_compute_statistic', string='Valid Sms Contacts')


    @api.depends('contact_ids')
    def _compute_statistic(self):
        for sms_list in self:
            contact_ids = sms_list.contact_ids.with_context({'default_list_ids': [sms_list.id]})
            sms_list.contact_ids_opt_out = contact_ids.filtered('opt_out')
            contact_ids_mail_blacklisted = contact_ids.filtered('is_blacklisted')
            contact_ids_mobile_blacklisted = contact_ids.filtered('phone_sanitized_blacklisted')
            sms_list.contact_ids_blacklisted = contact_ids_mail_blacklisted | contact_ids_mobile_blacklisted
            sms_list.contact_ids_message_bounce = contact_ids.filtered('message_bounce')
            sms_list.contact_ids_valid_email = contact_ids.filtered(
                lambda contact: contact.email and not contact.is_blacklisted and not contact.opt_out
            )
            sms_list.contact_ids_valid_sms = contact_ids.filtered(
                lambda contact: contact.mobile and not contact.is_blacklisted and not contact.opt_out
            )
            sms_list.contact_ids_valid = sms_list.contact_ids_valid_email | sms_list.contact_ids_valid_sms

            sms_list.contact_count = len(contact_ids)
            sms_list.contact_valid_email_count = len(sms_list.contact_ids_valid_email)
            sms_list.contact_valid_sms_count = len(sms_list.contact_ids_valid_sms)
            sms_list.contact_valid_count = len(sms_list.contact_ids_valid)
            sms_list.mailing_list_count = len(sms_list.mailing_list_ids)

            sms_list.contact_message_bounce_percentage = fields.float_round(
                len(sms_list.contact_ids_message_bounce) / sms_list.contact_count * 100, 2
            ) if sms_list.contact_count > 0 else 0
            sms_list.contact_blacklist_percentage = fields.float_round(
                len(sms_list.contact_ids_blacklisted) / sms_list.contact_count * 100, 2
            ) if sms_list.contact_count > 0 else 0
            sms_list.contact_opt_out_percentage = fields.float_round(
                len(sms_list.contact_ids_opt_out) / sms_list.contact_count * 100, 2
            ) if sms_list.contact_count > 0 else 0

            sms_list.contact_message_bounce_percentage_str = str(sms_list.contact_message_bounce_percentage) + '%'
            sms_list.contact_opt_out_percentage_str = str(sms_list.contact_opt_out_percentage) + '%'
            sms_list.contact_blacklist_percentage_str = str(sms_list.contact_blacklist_percentage) + '%'


    def action_view_valid_sms_contacts(self):
        action = self.env.ref('mass_mailing_sms.mailing_contact_action_sms').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(
            self.env.context,
            default_list_ids=self.ids,
            search_default_filter_valid_sms=1,
        )
        return action

    def action_view_valid_contacts(self):
        action = self.env.ref('mass_mailing_sms.mailing_contact_action_sms').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(
            self.env.context,
            default_list_ids=self.ids,
            search_default_filter_valid_email_sms=1,
        )
        return action

    def action_view_blacklisted_contacts(self):
        action = self.env.ref('mass_mailing.action_view_mass_mailing_contacts').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(
            self.env.context,
            default_list_ids=self.ids,
            search_default_filter_blacklisted=1,
            search_default_filter_phone_blacklisted=1,
        )
        return action
