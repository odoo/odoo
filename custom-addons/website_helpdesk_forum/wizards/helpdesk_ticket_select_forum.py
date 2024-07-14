# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicketSelectForumWizard(models.TransientModel):
    _name = "helpdesk.ticket.select.forum.wizard"
    _description = 'Share on Forum'

    ticket_id = fields.Many2one('helpdesk.ticket', default=lambda self: self.env.context.get('active_id'))
    forum_id = fields.Many2one('forum.forum', required=True, domain="[('filter_for_helpdesk_wizard', '=', True)]")

    title = fields.Char(compute='_compute_post', store=True, readonly=False, required=True)
    description = fields.Html(compute='_compute_post', store=True, readonly=False, required=True)
    tag_ids = fields.Many2many('forum.tag', string='Tags', compute='_compute_post', store=True, readonly=False)

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'forum_id' in fields_list:
            res['forum_id'] = self.env['forum.forum'].search([('filter_for_helpdesk_wizard', '=', True)], limit=1).id
        return res

    def action_confirm_selection(self):
        if not self.forum_id:
            raise UserError(_('You must select a forum to share the ticket'))
        return self.ticket_id._share_ticket_on_forums(self.forum_id)

    @api.depends('ticket_id')
    def _compute_post(self):
        tags_lower = self.ticket_id.tag_ids.mapped(lambda t: t and t.name.lower())
        all_tags = {}
        if tags_lower:
            self.env.cr.execute("""SELECT id, LOWER(name) FROM forum_tag WHERE LOWER(name) IN %s""", (tuple(tags_lower), ))
            all_tags = {t[1]: t[0] for t in self.env.cr.fetchall()}

        for wizard in self:
            wizard.title = wizard.ticket_id.name
            wizard.description = wizard.ticket_id.description

            ticket_tags = wizard.ticket_id.tag_ids.mapped(lambda t: t and t.name.lower())
            wizard.write({
                'tag_ids': [(6, 0, [all_tags[t] for t in ticket_tags if t in all_tags])]
            })

    def _create_forum_post(self):
        self.ensure_one()
        self.ticket_id.team_id._ensure_help_center_is_activated()

        forum_post = self.env['forum.post'].create({
            'name': self.title,
            'forum_id': self.forum_id.id,
            'content': self.description,
            'ticket_id': self.ticket_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)]
        })
        body = Markup("<a href='/forum/%s/question/%s'>%s</a> %s") % (
            self.forum_id.id, forum_post.id, forum_post.name, _('Forum Post created'))
        self.ticket_id.message_post(body=body)
        self.ticket_id.write({
            'forum_post_ids': [(4, forum_post.id, 0)]
        })

        for post in forum_post:
            post.message_post_with_source(
                'helpdesk.ticket_creation',
                render_values={'self': post, 'ticket': self.ticket_id},
                subtype_xmlid='mail.mt_note',
            )

        return forum_post

    def action_create_post(self):
        self._create_forum_post()
        return {'type': 'ir.actions.act_window_close'}

    def action_create_view_post(self):
        return self._create_forum_post().open_forum_post()


class ForumForum(models.Model):
    _inherit = "forum.forum"

    filter_for_helpdesk_wizard = fields.Boolean(store=False, search='_search_filter_for_helpdesk_wizard')

    def _search_filter_for_helpdesk_wizard(self, operator, value):
        assert operator == '='
        assert value

        forums = False
        ticket_id = self.env.context.get('active_id')
        if ticket_id:
            forums = self.env['helpdesk.ticket'].browse(ticket_id).team_id.sudo().website_forum_ids
        return [] if not forums else [('id', 'in', forums.ids)]
