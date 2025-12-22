from odoo import _, api, exceptions, fields, models, osv


class MassMailing(models.Model):
    _name = 'mailing.mailing'
    _inherit = 'mailing.mailing'

    mailing_model_id = fields.Many2one(compute="_compute_mailing_model_id", store=True, readonly=False)
    card_requires_sync_count = fields.Integer(compute="_compute_card_requires_sync_count")
    card_campaign_id = fields.Many2one('card.campaign')

    @api.constrains('card_campaign_id', 'mailing_domain', 'mailing_model_id')
    def _check_mailing_domain(self):
        for mailing in self:
            if mailing.card_campaign_id:
                if mailing.sudo().mailing_model_id.model != mailing.card_campaign_id.res_model:
                    raise exceptions.ValidationError(_(
                        "Card Campaign Mailing should target model %(model_name)s",
                        model_name=self.env['ir.model']._get(mailing.card_campaign_id.res_model).display_name
                    ))

    @api.depends('card_campaign_id')
    def _compute_mailing_model_id(self):
        for mailing in self.filtered('card_campaign_id'):
            mailing.mailing_model_id = self.env['ir.model']._get_id(mailing.card_campaign_id.res_model)

    @api.depends('card_campaign_id')
    def _compute_card_requires_sync_count(self):
        """Check if there's any missing or outdated card."""
        self.card_requires_sync_count = 0
        # no point in updating sent mailings
        card_mailings = self.filtered(lambda mailing: mailing.card_campaign_id and mailing.state == 'draft')
        for mailing in card_mailings:
            recipients = self.env[mailing.mailing_model_real].search(self._parse_mailing_domain())
            out_of_date_count = self.env['card.card'].search_count([
                ('campaign_id', '=', mailing.card_campaign_id.id),
                ('res_id', 'in', recipients.ids),
                ('requires_sync', '=', False)
            ])
            mailing.card_requires_sync_count = len(recipients) - out_of_date_count

    def action_put_in_queue(self):
        """Detect mismatches before scheduling."""
        for mailing in self.filtered('card_campaign_id'):
            if mailing.card_requires_sync_count:
                raise exceptions.UserError(_(
                    'You should update all the cards for %(mailing)s before scheduling a mailing.',
                    mailing=mailing.display_name
                ))
        super().action_put_in_queue()

    def action_send_mail(self, res_ids=None):
        for mailing in self.filtered('card_campaign_id'):
            if mailing.card_requires_sync_count:
                raise exceptions.UserError(_(
                    'You should update all the cards for %(mailing)s before scheduling a mailing.',
                    mailing=mailing.display_name
                ))
        return super().action_send_mail(res_ids)

    def action_update_cards(self):
        """Update the cards in batches, commiting after each batch."""
        for campaign in self.filtered(lambda mailing: mailing.state == 'draft').card_campaign_id:
            campaign._update_cards(self._parse_mailing_domain(), auto_commit=True)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mailing.mailing',
            'res_id': self[0].id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_recipients_domain(self):
        """Domain with an additional condition that the card must exist for the records."""
        domain = super()._get_recipients_domain()
        if self.card_campaign_id:
            res_ids = self.env['card.card'].search_fetch([('campaign_id', '=', self.card_campaign_id.id)], ['res_id']).mapped('res_id')
            domain = osv.expression.AND([domain, [('id', 'in', res_ids)]])
        return domain
