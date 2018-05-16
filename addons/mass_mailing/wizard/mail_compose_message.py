# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)
EMAIL_PATTERN = '([^ ,;<@]+@[^> ,;]+)'

class MailComposeMessage(models.TransientModel):
    """Add concept of mass mailing campaign to the mail.compose.message wizard
    """
    _inherit = 'mail.compose.message'

    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing', ondelete='cascade')
    mass_mailing_name = fields.Char(string='Mass Mailing Name')
    mailing_list_ids = fields.Many2many('mail.mass_mailing.list', string='Mailing List')

    @api.multi
    def get_mail_values(self, res_ids):
        """ Override method that generated the mail content by creating the
        mail.mail.statistics values in the o2m of mail_mail, when doing pure
        email mass mailing. """
        self.ensure_one()
        res = super(MailComposeMessage, self).get_mail_values(res_ids)
        # use only for allowed models in mass mailing
        if self.composition_mode == 'mass_mail' and \
                (self.mass_mailing_name or self.mass_mailing_id) and \
                self.env['ir.model'].sudo().search([('model', '=', self.model), ('is_mail_thread', '=', True)], limit=1):
            mass_mailing = self.mass_mailing_id
            if not mass_mailing:
                reply_to_mode = 'email' if self.no_auto_thread else 'thread'
                reply_to = self.reply_to if self.no_auto_thread else False
                mass_mailing = self.env['mail.mass_mailing'].create({
                        'mass_mailing_campaign_id': self.mass_mailing_campaign_id.id,
                        'name': self.mass_mailing_name,
                        'template_id': self.template_id.id,
                        'state': 'done',
                        'reply_to_mode': reply_to_mode,
                        'reply_to': reply_to,
                        'sent_date': fields.Datetime.now(),
                        'body_html': self.body,
                        'mailing_model_id': self.env['ir.model']._get(self.model).id,
                        'mailing_domain': self.active_domain,
                })

            # Preprocess res.partners to batch-fetch from db
            # if recipient_ids is present, it means they are partners
            # (the only object to fill get_default_recipient this way)
            recipient_partners_ids = []
            read_partners = {}
            for res_id in res_ids:
                mail_values = res[res_id]
                if mail_values.get('recipient_ids'):
                    # recipient_ids is a list of x2m command tuples at this point
                    recipient_partners_ids.append(mail_values.get('recipient_ids')[0][1])
            read_partners = self.env['res.partner'].browse(recipient_partners_ids)

            partners_email = {p.id: p.email for p in read_partners}

            unsubscribed_list = self._context.get('mass_mailing_unsubscribed_list')
            seen_list = self._context.get('mass_mailing_seen_list')
            total_blacklisted_email = 0
            for res_id in res_ids:
                mail_values = res[res_id]
                if mail_values.get('email_to'):
                    recips = tools.email_split(mail_values['email_to'])
                else:
                    recips = tools.email_split(partners_email.get(res_id))
                mail_to = recips[0].lower() if recips else False
                # implement a global blacklist table, to easily share it and update it.
                if mail_to and self.env['mail.mass_mailing.blacklist'].search([('email', '=', mail_to)]):
                    mail_values['state'] = 'cancel'
                    total_blacklisted_email += 1
                # prevent sending to blocked addresses that were included by mistake. Also prevent to send mail to invalid email address.
                elif (unsubscribed_list and mail_to in unsubscribed_list) \
                        or (seen_list and mail_to in seen_list) \
                        or (not mail_to or not re.match(EMAIL_PATTERN, mail_to)):
                    mail_values['state'] = 'cancel'
                elif seen_list is not None:
                    seen_list.add(mail_to)

                stat_vals = {
                    'model': self.model,
                    'res_id': res_id,
                    'mass_mailing_id': mass_mailing.id
                }
                # propagate ignored state to stat when still-born
                if mail_values.get('state', 'None') == 'cancel':
                    stat_vals['ignored'] = fields.Datetime.now()
                mail_values.update({
                    'mailing_id': mass_mailing.id,
                    'statistics_ids': [(0, 0, stat_vals)],
                    # email-mode: keep original message for routing
                    'notification': mass_mailing.reply_to_mode == 'thread',
                    'auto_delete': not mass_mailing.keep_archives,
                })

            if total_blacklisted_email:
                _logger.info("Mailing %s targets blacklist: %s emails", self.model, total_blacklisted_email)
            else:
                _logger.info("Mailing %s targets no blacklist available", self.model)

        return res
