# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class LoyaltyWebsiteRedeemedReward(models.Model):
    _name = 'loyalty.website.redeemed.reward'
    _description = 'Loyalty Website Redeemed Reward'

    partner_id = fields.Many2one('res.partner', required=True)
    website_id = fields.Many2one('website', ondelete='cascade', required=True)
    name = fields.Char(help="Name of the reward at redeemed time", required=True)
    point_used = fields.Float(string='Points Used', help="Cost of the reward in points at redeemed time")
    gift_card_id = fields.Many2one('gift.card', required=True)

    def _send_gift_card_mail(self):
        template = self.env.ref('sale_gift_card.mail_template_gift_card', raise_if_not_found=False)
        if template:
            template.send_mail(self.gift_card_id.id, notif_layout='mail.mail_notification_light',
                force_send=True,
                email_values={
                    'email_to': self.partner_id.email,
                    'email_from': self.website_id.company_id.email_formatted,
                    'author_id': self.partner_id.id,
                    'subject': _('Gift card information'),
                },
            )
