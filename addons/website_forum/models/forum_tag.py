# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections.abc import Iterable

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ForumTag(models.Model):
    _name = 'forum.tag'
    _description = "Forum Tag"
    _inherit = [
        'website.searchable.mixin',
        'website.located.mixin',
        'website.seo.metadata',
    ]

    name = fields.Char('Name', required=True)
    color = fields.Integer('Color')
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True, index=True)
    post_ids = fields.Many2many(
        'forum.post', 'forum_tag_rel', 'forum_tag_id', 'forum_post_id',
        string='Posts', domain=[('state', '=', 'active')])
    posts_count = fields.Integer('Number of Posts', compute='_compute_posts_count', store=True)
    _name_uniq = models.Constraint(
        'unique (name, forum_id)',
        'Tag name already exists!',
    )

    follower_ids = fields.Many2many(
        'res.partner',
        'forum_tag_follower_rel',
        string="Followers",
        groups="base.group_erp_manager",
    )
    is_follower = fields.Boolean(
        compute="_compute_is_follower",
        inverse="_inverse_is_follower",
        search="_search_is_follower",
        string="Is Follower",
    )

    @api.depends_context('uid')
    @api.depends("follower_ids")
    def _compute_is_follower(self):
        partner = self.env['forum.post']._get_current_partner()
        followed = self.sudo().search([
            ('id', 'in', self.ids),
            ('follower_ids', '=', partner.id),
        ])
        (self & followed).is_follower = True  # update record in `self`
        (self - followed).is_follower = False

    def _inverse_is_follower(self):
        partner = self.env['forum.post']._get_current_partner()
        for post in self:
            if post.is_follower:
                post.sudo().follower_ids |= partner
            else:
                post.sudo().follower_ids -= partner

    def _search_is_follower(self, operator, value):
        if operator != 'in' or not isinstance(value, Iterable) or tuple(value) != (True,):
            return NotImplemented
        domain = [('follower_ids', '=', self.env.user.partner_id.id)]
        return [('id', 'in', self.sudo()._search(domain))]

    @api.depends("post_ids", "post_ids.tag_ids", "post_ids.state", "post_ids.active")
    def _compute_posts_count(self):
        for tag in self:
            tag.posts_count = len(tag.post_ids)  # state filter is in field domain

    @api.depends("forum_id", "forum_id.name", "name")
    def _compute_website_url(self):
        for tag in self:
            tag.website_url = f'/forum/{self.env["ir.http"]._slug(tag.forum_id)}/tag/{self.env["ir.http"]._slug(tag)}/questions'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            forum = self.env['forum.forum'].browse(vals.get('forum_id'))
            if self.env.user.karma < forum.karma_tag_create and not self.env.is_admin():
                raise AccessError(_('%d karma required to create a new Tag.', forum.karma_tag_create))
        return super(ForumTag, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(vals_list)

    # ----------------------------------------------------------------------
    # WEBSITE
    # ----------------------------------------------------------------------

    @api.model
    def _search_get_detail(self, website, order, options):
        search_fields = ['name']
        fetch_fields = ['id', 'name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }
        base_domain = []
        if forum := options.get("forum"):
            forum_ids = (self.env['ir.http']._unslug(forum)[1],) if isinstance(forum, str) else forum.ids
            search_domain = options.get("domain")
            base_domain = [search_domain if search_domain is not None else [('forum_id', 'in', forum_ids)]]
        return {
            'model': 'forum.tag',
            'base_domain': base_domain,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-tag',
            'order': ','.join(filter(lambda f: 'is_published' not in f, order.split(','))),
        }
