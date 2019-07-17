# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools
from odoo.tools import email_re


class MailComposeMessage(models.TransientModel):
    """Add concept of mass mailing campaign to the mail.compose.message wizard
    """
    _inherit = 'mail.compose.message'

    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing', ondelete='cascade')
    mass_mailing_name = fields.Char(string='Mass Mailing Name')
    mailing_list_ids = fields.Many2many('mail.mass_mailing.list', string='Mailing List')

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

            opt_out_list = self._context.get('mass_mailing_opt_out_list')
            seen_list = self._context.get('mass_mailing_seen_list')
            mass_mail_layout = self.env.ref('mass_mailing.mass_mailing_mail_layout', raise_if_not_found=False)
            for res_id in res_ids:
                mail_values = res[res_id]
                if mail_values.get('email_to'):
                    mail_to = tools.email_normalize(mail_values['email_to'])
                else:
                    partner_id = (mail_values.get('recipient_ids') or [(False, '')])[0][1]
                    mail_to = tools.email_normalize(partners_email.get(partner_id))
                if (opt_out_list and mail_to in opt_out_list) or (seen_list and mail_to in seen_list) \
                        or (not mail_to or not email_re.findall(mail_to)):
                    # prevent sending to blocked addresses that were included by mistake
                    mail_values['state'] = 'cancel'
                elif seen_list is not None:
                    seen_list.add(mail_to)
                stat_vals = {
                    'model': self.model,
                    'res_id': res_id,
                    'mass_mailing_id': mass_mailing.id,
                    'email': mail_to,
                }
                if mail_values.get('body_html') and mass_mail_layout:
                    mail_values['body_html'] = mass_mail_layout.render({'body': mail_values['body_html']}, engine='ir.qweb', minimal_qcontext=True)
                # propagate ignored state to stat when still-born
                if mail_values.get('state') == 'cancel':
                    stat_vals['ignored'] = fields.Datetime.now()
                mail_values.update({
                    'mailing_id': mass_mailing.id,
                    'statistics_ids': [(0, 0, stat_vals)],
                    # email-mode: keep original message for routing
                    'notification': mass_mailing.reply_to_mode == 'thread',
                    'auto_delete': not mass_mailing.keep_archives,
                })
        return res
