# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models, _

# bot click: another link, or the hidden link from the same IP, clicked that close
MULTI_LINK_INTERVAL = timedelta(seconds=2)
HIDDEN_LINK_WINDOW = timedelta(seconds=10)


class LinkTracker(models.Model):
    _inherit = "link.tracker"

    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    mailing_trace_id = fields.Many2one('mailing.trace', string='Mail Statistics', index='btree_not_null')
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing', index='btree_not_null')
    email = fields.Char(string="Email", related="mailing_trace_id.email", help="The email address of the entity that clicked the link")
    url = fields.Char(string='URL', related='link_id.url')
    bot_check_pending = fields.Boolean('Bot Check Pending', readonly=True)

    _bot_check_pending_idx = models.Index('(create_date) WHERE bot_check_pending IS TRUE')

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

        if click and click.bot_check_pending:
            # opened / clicked only once confirmed, see '_cron_check_pending_clicks'
            self.env.ref('mass_mailing.ir_cron_mass_mailing_pending_clicks')._trigger(
                click.create_date + HIDDEN_LINK_WINDOW)
        elif click and click.mailing_trace_id:
            click.mailing_trace_id.set_opened()
            click.mailing_trace_id.set_clicked()

        return click

    @api.model
    def _cron_check_pending_clicks(self, batch_size=1000):
        """ Confirm held clicks, or delete those made by bots. """
        domain = [('bot_check_pending', '=', True), ('create_date', '<=', self.env.cr.now() - HIDDEN_LINK_WINDOW)]
        pending_clicks = self.search(domain, limit=batch_size)
        # also newer clicks of the same emails, to delete a bot's clicks together
        email_clicks = self.search([
            ('mailing_trace_id', 'in', pending_clicks.mailing_trace_id.ids),
            ('create_date', '>=', min(pending_clicks.mapped('create_date'), default=self.env.cr.now()) - MULTI_LINK_INTERVAL),
        ])

        bot_clicks = self.browse()
        for trace, trace_clicks in email_clicks.grouped('mailing_trace_id').items():
            for click in trace_clicks:
                near_hidden_link = (
                    trace.hidden_link_click_datetime
                    and click.ip == trace.hidden_link_click_ip
                    and abs(click.create_date - trace.hidden_link_click_datetime) <= HIDDEN_LINK_WINDOW
                )
                near_other_link = any(
                    other.link_id != click.link_id and abs(other.create_date - click.create_date) <= MULTI_LINK_INTERVAL
                    for other in trace_clicks
                )
                if near_hidden_link or near_other_link:
                    bot_clicks |= click
        # already confirmed clicks are kept
        bot_clicks = bot_clicks.filtered('bot_check_pending')
        human_clicks = pending_clicks - bot_clicks

        bot_clicks.unlink()
        human_clicks.bot_check_pending = False
        human_clicks.mailing_trace_id.set_opened()
        human_clicks.mailing_trace_id.set_clicked()

        self.env['ir.cron']._commit_progress(
            len(pending_clicks),
            remaining=self.search_count(domain) if len(pending_clicks) == batch_size else 0,
        )

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
