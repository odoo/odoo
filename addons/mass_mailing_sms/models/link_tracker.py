# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    sms_statistics_id = fields.Many2one('sms.statistics', string='SMS Statistics', ondelete='set null')

    def _prepare_click_values_from_route(self, **route_values):
        click_values = super(LinkTrackerClick, self)._prepare_click_values_from_route(**route_values)

        if click_values.get('sms_statistics_id'):
            sms_sudo = self.env['sms.statistics'].sudo().browse(route_values['sms_statistics_id']).exists()
            if not sms_sudo:
                click_values['sms_statistics_id'] = False
            else:
                if not click_values.get('mass_mailing_campaign_id'):
                    click_values['mass_mailing_campaign_id'] = sms_sudo.mass_mailing_campaign_id.id
                if not click_values.get('mass_mailing_id'):
                    click_values['mass_mailing_id'] = sms_sudo.mass_mailing_id.id

        return click_values

    @api.model
    def add_click(self, code, **route_values):
        click = super(LinkTrackerClick, self).add_click(code, **route_values)

        if click and click.sms_statistics_id:
            click.sms_statistics_id.set_clicked()

        return click
