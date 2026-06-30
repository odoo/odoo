# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingList(models.Model):
    _inherit = 'mailing.list'

    contact_count_sms = fields.Integer(compute="_compute_mailing_list_statistics", string="SMS Contacts")

    def action_view_mailings(self):
        if self.env.context.get('mailing_sms'):
            action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing_sms.mailing_mailing_action_sms')
            action['domain'] = [('id', 'in', self.mailing_ids.ids)]
            action['context'] = {
                'default_mailing_type': 'sms',
                'default_contact_list_ids': self.ids,
                'mailing_sms': True
            }
            return action
        else:
            return super(MailingList, self).action_view_mailings()

    def action_view_contacts_sms(self):
        action = self.action_view_contacts()
        action['context'] = dict(action.get('context', {}), search_default_filter_valid_sms_recipient=1)
        return action

    def action_send_mailing_sms(self):
        view = self.env.ref('mass_mailing_sms.mailing_mailing_view_form_sms')
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing_sms.mailing_mailing_action_sms')
        action.update({
            'context': {
                'default_contact_list_ids': self.ids,
                'default_model_id': self.env['ir.model']._get_id('mailing.list'),
                'default_mailing_type': 'sms',
            },
            'target': 'current',
            'view_type': 'form',
            'views': [(view.id, 'form')],
        })

        return action

    def _get_contact_statistics_fields(self):
        """ See super method docstring for more info.
        Adds:
        - contact_count_sms:           all valid sms
        - contact_count_blacklisted:   override the dict entry to add SMS blacklist condition """

        values = super(MailingList, self)._get_contact_statistics_fields()
        values.update({
            'contact_count_sms': '''
                SUM(CASE WHEN
                    (c.phone_sanitized IS NOT NULL
                    AND COALESCE(r.opt_out,FALSE) = FALSE
                    AND bl_sms.id IS NULL)
                THEN 1 ELSE 0 END) AS contact_count_sms''',
            'contact_count_blacklisted': '''
                SUM(CASE WHEN (bl.id IS NOT NULL OR bl_sms.id IS NOT NULL)
                THEN 1 ELSE 0 END) AS contact_count_blacklisted'''
        })
        return values

    def _get_contact_statistics_joins(self):
        return super(MailingList, self)._get_contact_statistics_joins() + '''
            LEFT JOIN phone_blacklist bl_sms ON c.phone_sanitized = bl_sms.number and bl_sms.active
        '''

    def _mailing_get_opt_out_list_sms(self, mailing):
        """ Check subscription on all involved mailing lists. If user is opt_out
        on one list but not on another, one opted in and the other one opted out,
        send mailing anyway.

        :return: opt-outed record IDs
        :rtype: list
        """
        subscriptions = self.subscription_ids if self else mailing.contact_list_ids.subscription_ids
        opt_out_contacts = subscriptions.filtered(lambda sub: sub.opt_out).mapped('contact_id')
        opt_in_contacts = subscriptions.filtered(lambda sub: not sub.opt_out).mapped('contact_id')
        return list(set(c.id for c in opt_out_contacts if c not in opt_in_contacts))
