# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LinkTracker(models.Model):
    _inherit = "link.tracker"

    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')

    def _search_and_update(self, vals):
        """ We override this method as searching with mass_mailing_id will not find the linked record.
            If the linked record is found, we then update its mass_mailing_id.
        """
        search_vals = vals.copy()
        has_mass_mailing = 'mass_mailing_id' in vals

        if has_mass_mailing:
            mass_mailing_id = search_vals.pop('mass_mailing_id')

        search_domain = []
        for fname, value in search_vals.items():
            search_domain.append((fname, '=', value))

        result = self.search(search_domain, limit=1)

        if result and has_mass_mailing:
            result.write({'mass_mailing_id': mass_mailing_id})

        return result


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    mailing_trace_id = fields.Many2one('mailing.trace', string='Mail Statistics')
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')

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
