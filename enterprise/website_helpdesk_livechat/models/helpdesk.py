# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup

from odoo import Command, fields, models, _
from odoo.tools import is_html_empty, plaintext2html
from odoo.osv.expression import OR

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
        msg = _('Something is missing or wrong in the command')
        partners = self.with_context(active_test=False).channel_partner_ids.filtered(lambda partner: partner != self.env.user.partner_id)
        ticket_command = "/ticket"
        if key[0].lower() == ticket_command:
            if len(key) == 1:
                msg = _(
                    "Create a new helpdesk ticket by typing: "
                    "%(pre_start)s%(ticket_command)s %(i_start)sticket title%(i_end)s%(pre_end)s",
                    ticket_command=ticket_command,
                    pre_start=Markup("<pre>"),
                    pre_end=Markup("</pre>"),
                    i_start=Markup("<i>"),
                    i_end=Markup("</i>"),
                )
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
        self.env.user._bus_send_transient_message(self, msg)

    def fetch_ticket_by_keyword(self, list_keywords, load_counter=0):
        keywords = re.findall(r'\w+', ' '.join(list_keywords))
        helpdesk_tag_ids = self.env['helpdesk.tag'].search(
            OR([[('name', 'ilike', keyword)] for keyword in keywords])
        ).ids
        tickets = self.env['helpdesk.ticket'].search([('tag_ids', 'in', helpdesk_tag_ids)], offset=load_counter*5, limit=6, order='id desc')
        if not tickets:
            for Keyword in keywords:
                tickets |= self.env['helpdesk.ticket'].search([
                    '|', '|', '|', '|', '|',
                    ('name', 'ilike', Keyword),
                    ('ticket_ref', 'ilike', Keyword),
                    ('partner_id.id', 'ilike', Keyword),
                    ('partner_name', 'ilike', Keyword),
                    ('partner_email', 'ilike', Keyword),
                    ('partner_phone', 'ilike', Keyword),
                ], order="id desc", offset=load_counter*5, limit=6 - len(tickets))
        if not tickets:
            return False
        load_more = False
        if len(tickets) > 5:
            tickets = tickets[:-1]
            load_more = True
        msg = Markup('<br/>').join(ticket.with_context(with_partner=True)._get_html_link() for ticket in tickets)
        if load_more:
            msg += Markup('<br/>')
            msg += Markup('<div class="o_load_more"><b><a href="#" data-oe-type="load" data-oe-lst="%s" data-oe-load-counter="%s">%s</a></b></div>') % (
                ' '.join(list_keywords),
                load_counter + 1,
                _('Load More')
            )
        return msg

    def execute_command_helpdesk_search(self, **kwargs):
        key = kwargs.get('body').split()
        partner = self.env.user.partner_id
        msg = _('Something is missing or wrong in command')
        search_tickets_command = "/search_tickets"
        if key[0].lower() == search_tickets_command:
            if len(key) == 1:
                msg = _(
                    "Search helpdesk tickets by typing: "
                    "%(pre_start)s%(search_tickets_command)s %(i_start)skeywords%(i_end)s%(pre_end)s",
                    search_tickets_command=search_tickets_command,
                    pre_start=Markup("<pre>"),
                    pre_end=Markup("</pre>"),
                    i_start=Markup("<i>"),
                    i_end=Markup("</i>"),
                )
            else:
                list_keywords = key[1:]
                tickets = self.fetch_ticket_by_keyword(list_keywords)
                if tickets:
                    msg = _(
                        "Tickets search results for %(b_start)s%(keywords)s%(b_end)s: %(br)s%(tickets)s",
                        keywords=" ".join(list_keywords),
                        b_start=Markup("<b>"),
                        b_end=Markup("</b>"),
                        br=Markup("<br/>"),
                        tickets=tickets,
                    )
                else:
                    msg = _(
                        "No tickets found for %(b_start)s%(keywords)s%(b_end)s.%(br)s"
                        "Make sure you are using the right format: "
                        "%(pre_start)s%(search_tickets_command)s %(i_start)skeywords%(i_end)s%(pre_end)s",
                        keywords=" ".join(list_keywords),
                        b_start=Markup("<b>"),
                        b_end=Markup("</b>"),
                        br=Markup("<br/>"),
                        search_tickets_command=search_tickets_command,
                        pre_start=Markup("<pre>"),
                        pre_end=Markup("</pre>"),
                        i_start=Markup("<i>"),
                        i_end=Markup("</i>"),
                    )
        partner._bus_send_transient_message(self, msg)
