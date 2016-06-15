# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
    """Add concept of mass mailing campaign to the mail.compose.message wizard
    """
    _inherit = 'mail.compose.message'

    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing', ondelete='cascade')
    mass_mailing_name = fields.Char(string='Mass Mailing')
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
                self.model in [item[0] for item in self.env['mail.mass_mailing']._get_mailing_model()]:
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
                        'mailing_model': self.model,
                        'mailing_domain': self.active_domain,
                })
            for res_id in res_ids:
                res[res_id].update({
                    'mailing_id': mass_mailing.id,
                    'statistics_ids': [(0, 0, {
                        'model': self.model,
                        'res_id': res_id,
                        'mass_mailing_id': mass_mailing.id,
                    })],
                    # email-mode: keep original message for routing
                    'notification': mass_mailing.reply_to_mode == 'thread',
                    'auto_delete': not mass_mailing.keep_archives,
                })
        return res
