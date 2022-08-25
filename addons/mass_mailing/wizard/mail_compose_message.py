# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing', ondelete='cascade')
    campaign_id = fields.Many2one('utm.campaign', string='Mass Mailing Campaign', ondelete='set null')
    mass_mailing_name = fields.Char(string='Mass Mailing Name', help='If set, a mass mailing will be created so that you can track its results in the Email Marketing app.')
    mailing_list_ids = fields.Many2many('mailing.list', string='Mailing List')

    def get_mail_values(self, res_ids):
        """ Override method that generated the mail content by creating the
        mailing.trace values in the o2m of mail_mail, when doing pure
        email mass mailing. """
        now = fields.Datetime.now()
        self.ensure_one()
        res = super(MailComposeMessage, self).get_mail_values(res_ids)
        # use only for allowed models in mass mailing
        if self.composition_mode == 'mass_mail' and \
                (self.mass_mailing_name or self.mass_mailing_id) and \
                self.env['ir.model'].sudo().search_count([('model', '=', self.model), ('is_mail_thread', '=', True)]):
            mass_mailing = self.mass_mailing_id
            if not mass_mailing:
                mass_mailing = self.env['mailing.mailing'].create({
                    'campaign_id': self.campaign_id.id,
                    'name': self.mass_mailing_name,
                    'subject': self.subject,
                    'state': 'done',
                    'reply_to_mode': self.reply_to_mode,
                    'reply_to': self.reply_to if self.reply_to_mode == 'new' else False,
                    'sent_date': now,
                    'body_html': self.body,
                    'mailing_model_id': self.env['ir.model']._get(self.model).id,
                    'mailing_domain': self.active_domain,
                    'attachment_ids': [(6, 0, self.attachment_ids.ids)],
                })
                self.mass_mailing_id = mass_mailing.id

            recipients_info = self._process_recipient_values(res)
            for res_id in res_ids:
                mail_values = res[res_id]
                if mail_values.get('body_html'):
                    body = self.env['ir.qweb']._render('mass_mailing.mass_mailing_mail_layout',
                                {'body': mail_values['body_html']},
                                minimal_qcontext=True, raise_if_not_found=False)
                    if body:
                        mail_values['body_html'] = body

                trace_vals = {
                    'model': self.model,
                    'res_id': res_id,
                    'mass_mailing_id': mass_mailing.id,
                    # if mail_to is void, keep falsy values to allow searching / debugging traces
                    'email': recipients_info[res_id]['mail_to'][0] if recipients_info[res_id]['mail_to'] else '',
                }
                # propagate failed states to trace when still-born
                if mail_values.get('state') == 'cancel':
                    trace_vals['trace_status'] = 'cancel'
                elif mail_values.get('state') == 'exception':
                    trace_vals['trace_status'] = 'error'
                if mail_values.get('failure_type'):
                    trace_vals['failure_type'] = mail_values['failure_type']

                mail_values.update({
                    'mailing_id': mass_mailing.id,
                    'mailing_trace_ids': [(0, 0, trace_vals)],
                    # email-mode: keep original message for routing
                    'is_notification': mass_mailing.reply_to_mode == 'update',
                    'auto_delete': not mass_mailing.keep_archives,
                })
        return res

    def _get_done_emails(self, mail_values_dict):
        seen_list = super(MailComposeMessage, self)._get_done_emails(mail_values_dict)
        if self.mass_mailing_id:
            seen_list += self.mass_mailing_id._get_seen_list()
        return seen_list

    def _get_optout_emails(self, mail_values_dict):
        opt_out_list = super(MailComposeMessage, self)._get_optout_emails(mail_values_dict)
        if self.mass_mailing_id:
            opt_out_list += self.mass_mailing_id._get_opt_out_list()
        return opt_out_list
