# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LinkTracker(models.Model):
    _inherit = "link.tracker"

    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    mailing_trace_id = fields.Many2one('mailing.trace', string='Mail Statistics', index='btree_not_null')
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing', index='btree_not_null')

    def _prepare_click_values_from_route(self, **route_values):
        click_values = super(LinkTrackerClick, self)._prepare_click_values_from_route(**route_values)

        if click_values.get('mailing_trace_id'):
            trace_sudo = self.env['mailing.trace'].sudo().browse(route_values['mailing_trace_id']).exists()
            if not trace_sudo:
                click_values['mailing_trace_id'] = False
            else:
                if not click_values.get('campaign_id'):
                    click_values['campaign_id'] = trace_sudo.campaign_id.id
                if not click_values.get('mass_mailing_id'):
                    click_values['mass_mailing_id'] = trace_sudo.mass_mailing_id.id

        return click_values

    @api.model
    def add_click(self, code, **route_values):
        click = super(LinkTrackerClick, self).add_click(code, **route_values)

        if click and click.mailing_trace_id:
            click.mailing_trace_id.set_opened()
            click.mailing_trace_id.set_clicked()

        return click
