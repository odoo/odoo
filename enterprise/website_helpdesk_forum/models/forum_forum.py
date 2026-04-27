# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import fields, models, Command, _


class ForumForum(models.Model):
    _inherit = 'forum.forum'

    helpdesk_team_count = fields.Integer(compute='_compute_team_count', compute_sudo=True)
    helpdesk_team_ids = fields.Many2many('helpdesk.team', 'forum_forum_helpdesk_team_rel', 'forum_forum_id', 'helpdesk_team_id')

    def _compute_team_count(self):
        teams_count_per_forum_read_group = self.env['helpdesk.team']._read_group(
            [('website_forum_ids', 'in', self.ids)], ['website_forum_ids'], ['__count']
        )
        teams_count_per_forum_dict = dict(teams_count_per_forum_read_group)
        for forum in self:
            forum.helpdesk_team_count = teams_count_per_forum_dict.get(forum, 0)

    def action_open_helpdesk_team(self):
        self.ensure_one()
        return {
            'name': _('Helpdesk Teams'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.team',
            'views': [[False, "form"]] if self.helpdesk_team_count == 1 else [[False, "list"], [False, 'form']],
            'res_id': self.helpdesk_team_ids.id if self.helpdesk_team_count == 1 else None,
            'domain': [('website_forum_ids', '=', self.id)],
            'context': {
                'default_use_website_helpdesk_forum': True,
                'default_website_forum_ids': self.ids,
            }
        }

    def create_ticket(self, post_id, data):
        post = self.env['forum.post'].browse(post_id)
        ticket = self.env['helpdesk.ticket'].with_context(
            mail_create_nosubscribe=True,
            mail_create_nolog=True,
        ).create({
            'name': data['post_title'],
            'team_id': int(data['team_id']),
            'partner_id': int(data['post_creator_id']),
            'description': data['post_description'],
            'forum_post_ids': [Command.set(post.ids)],
        })

        post.ticket_id = ticket
        slug = self.env['ir.http']._slug
        ticket.message_post(
            body=Markup("%s <a href='/forum/%s/%s' target='_blank'>%s</a>") % (_('Ticket created from forum post'), slug(self), slug(post), post.name),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        return {
            'ticket': ticket.ticket_ref,
            'url': f"/odoo/{ticket._name}/{ticket.id}",
        }
