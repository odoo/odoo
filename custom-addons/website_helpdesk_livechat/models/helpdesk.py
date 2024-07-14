# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup

from odoo import Command, fields, models, _
from odoo.tools import html_escape, is_html_empty, plaintext2html


class HelpdeskTeam(models.Model):
    _inherit = ['helpdesk.team']

    use_website_helpdesk_livechat = fields.Boolean(inverse='_inverse_use_website_helpdesk_livechat')

    def _inverse_use_website_helpdesk_livechat(self):
        self._create_livechat_channel()

    # ------------------------------------------------------------
        #  Hooks
    # ------------------------------------------------------------
    def _create_livechat_channel(self):
        LiveChat = self.env['im_livechat.channel']
        channel_vals_per_team_name = {}
        for team in self:
            if not (team.name and team.use_website_helpdesk_livechat):
                continue
            if team.name not in channel_vals_per_team_name:
                vals = {'name': team.name}
                if team.member_ids and team.auto_assignment:
                    vals['user_ids'] = [Command.set(team.member_ids.ids)]
                channel_vals_per_team_name[team.name] = vals
        if channel_vals_per_team_name:
            channel_names = {
                res['name']
                for res in LiveChat.search_read([('name', 'in', list(channel_vals_per_team_name.keys()))], ['name'])
            }
            vals_list = [vals for team_name, vals in channel_vals_per_team_name.items() if team_name not in channel_names]
            if vals_list:
                LiveChat.create(vals_list)

    # ------------------------------------------------------------
        # action methods
    # ------------------------------------------------------------
    def action_view_channel(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('im_livechat.im_livechat_channel_action')
        channel_ids = list(self.env['im_livechat.channel']._search([('name', '=', self.name)], limit=1))
        if channel_ids:
            action.update(res_id=channel_ids[0], views=[(False, 'form')])
        return action

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    # ------------------------------------------------------
    #  Commands
    # ------------------------------------------------------

    def execute_command_helpdesk(self, **kwargs):
        key = kwargs.get('body').split()
        msg = _('Something is missing or wrong in command')
        partners = self.with_context(active_test=False).channel_partner_ids.filtered(lambda partner: partner != self.env.user.partner_id)
        if key[0].lower() == '/ticket':
            if len(key) == 1:
                msg = _("""
                    Create a new helpdesk ticket by typing <b>/ticket <i>ticket title</i></b><br>
                    """)
            else:
                customer = partners[:1]
                list_value = key[1:]
                description = ''
                odoobot = self.env.ref('base.partner_root')
                for message in self.message_ids.sorted(key=lambda r: r.id):
                    if is_html_empty(message.body) or message.author_id == odoobot:
                        continue
                    name = message.author_id.name or 'Anonymous'
                    description += '%s: ' % name + '%s\n' % re.sub('<[^>]*>', '', message.body)
                team = self.env['helpdesk.team'].search([('use_website_helpdesk_livechat', '=', True)], order='sequence', limit=1)
                team_id = team.id if team else False
                helpdesk_ticket = self.env['helpdesk.ticket'].with_context(with_partner=True).create({
                    'name': ' '.join(list_value),
                    'description': plaintext2html(description),
                    'partner_id': customer.id if customer else False,
                    'team_id': team_id,
                })
                msg = _("Created a new ticket: %s", helpdesk_ticket._get_html_link())
        return self._send_transient_message(self.env.user.partner_id, msg)

    def execute_command_helpdesk_search(self, **kwargs):
        key = kwargs.get('body').split()
        partner = self.env.user.partner_id
        msg = _('Something is missing or wrong in command')
        if key[0].lower() == '/search_tickets':
            if len(key) == 1:
                msg = _('Search helpdesk tickets by typing <b>/search_tickets <i>keyword</i></b>')
            else:
                list_value = key[1:]
                Keywords = re.findall(r'\w+', ' '.join(list_value))
                HelpdeskTag = self.env['helpdesk.tag']
                for Keyword in Keywords:
                    HelpdeskTag |= HelpdeskTag.search([('name', 'ilike', Keyword)])
                tickets = self.env['helpdesk.ticket'].search([('tag_ids', 'in', HelpdeskTag.ids)], limit=10)
                if not tickets:
                    for Keyword in Keywords:
                        tickets |= self.env['helpdesk.ticket'].search([
                            '|', '|', '|', '|', '|',
                            ('name', 'ilike', Keyword),
                            ('ticket_ref', 'ilike', Keyword),
                            ('partner_id.id', 'ilike', Keyword),
                            ('partner_name', 'ilike', Keyword),
                            ('partner_email', 'ilike', Keyword),
                            ('partner_phone', 'ilike', Keyword)
                        ], order="id desc", limit=10)
                        if len(tickets) > 10:
                            break
                if tickets:
                    msg = _('Tickets search results for %s: ', Markup("<b>%s</b>") % ' '.join(list_value))
                    msg += Markup('<br/>') + Markup('<br/>').join(ticket.with_context(with_partner=True)._get_html_link() for ticket in tickets)
                else:
                    msg = _('No tickets found for <b>%s</b>. <br> Make sure you are using the right format:<br> <b>/search_tickets <i>keyword</i></b>', ''.join(list_value))
                    msg = _('No tickets found for %s.', Markup("<b>%s</b>") % ''.join(list_value)) + \
                        Markup("<br>") + _("Make sure you are using the right format:") + Markup("<br> <b>/search_tickets <i>%s</i></b>") % _("keyword")
        return self._send_transient_message(partner, msg)
