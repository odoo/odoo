# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _


class LinkTracker(models.Model):
    _inherit = "link.tracker"

    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    mailing_trace_id = fields.Many2one('mailing.trace', string='Mail Statistics', index='btree_not_null')
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing', index='btree_not_null')
    email = fields.Char(string="Email", related="mailing_trace_id.email", help="The email address of the entity that clicked the link")
    url = fields.Char(string='URL', related='link_id.url')

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

    def _action_view_mailing_statistics(self, domain, group_by_field=None, graph_mode=False):
        """Display the click statistics for the given domain

        :param domain: the domain to be applied to filter the clicks.
        :param group_by_field: the field by which to group the clicks. E.g. `email`.
        By default, no grouping is applied.
        :param graph_mode: when `True`, the graph mode will be set to `pie`."""
        context = {**self.env.context, 'create': False}
        views = [(self.env.ref('mass_mailing.link_tracker_click_view_list_simplified').id, 'list')]
        view_mode = 'list'
        if graph_mode:
            context = {**self.env.context, 'graph_mode': 'pie', 'stacked': False}
            views.append((False, 'graph'))
            view_mode = f'{view_mode},graph'
        if group_by_field:
            group_by = f'search_default_groupby_{group_by_field}'
            context = {**self.env.context, f'{group_by}': True}
        helper_header = _("No Recipient clicked your mailing yet!")
        helper_message = _(
            "Come back once your mailing has been sent to track who clicked on the embedded links.")
        action = {
            'name': _('Link Clicks'),
            'type': 'ir.actions.act_window',
            'res_model': 'link.tracker.click',
            'view_mode': view_mode,
            'views': views,
            'domain': domain,
            'context': context,
        }
        action['help'] = Markup('<p class="o_view_nocontent_smiling_face">%s</p><p>%s</p>') % (
            helper_header, helper_message,
        )
        return action
