# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LinkTracker(models.Model):
    _inherit = "link.tracker"

    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    mail_stat_id = fields.Many2one('mail.mail.statistics', string='Mail Statistics')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')

    def _prepare_click_values_from_route(self, **route_values):
        click_values = super(LinkTrackerClick, self)._prepare_click_values_from_route(**route_values)

        if click_values.get('mail_stat_id'):
            stat_sudo = self.env['mail.mail.statistics'].sudo().browse(route_values['mail_stat_id']).exists()
            if not stat_sudo:
                click_values['mail_stat_id'] = False
            else:
                if not click_values.get('mass_mailing_campaign_id'):
                    click_values['mass_mailing_campaign_id'] = stat_sudo.mass_mailing_campaign_id.id
                if not click_values.get('mass_mailing_id'):
                    click_values['mass_mailing_id'] = stat_sudo.mass_mailing_id.id

        return click_values

    @api.model
    def add_click(self, code, **route_values):
        click = super(LinkTrackerClick, self).add_click(code, **route_values)

        if click and click.mail_stat_id:
            click.mail_stat_id.set_opened()
            click.mail_stat_id.set_clicked()

        return click
