# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import random

from odoo import api, models, fields, _
from odoo.addons.website.models.website import slug
from odoo.tools.translate import html_translate
from odoo.tools import html2plaintext


class Blog(models.Model):
    _name = 'blog.blog'
    _description = 'Blogs'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'name'

    name = fields.Char('Blog Name', required=True, translate=True)
    subtitle = fields.Char('Blog Subtitle', translate=True)
    active = fields.Boolean('Active', default=True)

    @api.multi
    def write(self, vals):
        res = super(Blog, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a blog does it on its posts, too
            post_ids = self.env['blog.post'].with_context(active_test=False).search([
                ('blog_id', 'in', self)
            ])
            post_ids.write({'active': vals['active']})
        return res

    @api.multi
    def all_tags(self, min_limit=1):
        req = """
            SELECT
                p.blog_id, count(*), r.blog_tag_id
            FROM
                blog_post_blog_tag_rel r
                    join blog_post p on r.blog_post_id=p.id
            WHERE
                p.blog_id in %s
            GROUP BY
                p.blog_id,
                r.blog_tag_id
            ORDER BY
                count(*) DESC
        """
        self._cr.execute(req, [tuple(self.ids)])
        tag_by_blog = {i.id: [] for i in self}
        for blog_id, freq, tag_id in self._cr.fetchall():
            if freq >= min_limit:
                tag_by_blog[blog_id].append(tag_id)

        BlogTag = self.env['blog.tag']
        for blog_id in tag_by_blog:
            tag_by_blog[blog_id] = BlogTag.browse(tag_by_blog[blog_id])
        return tag_by_blog


class BlogTag(models.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'

    name = fields.Char('Name', required=True)
    post_ids = fields.Many2many('blog.post', string='Posts')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class BlogPost(models.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin']
    _order = 'id DESC'
    _mail_post_access = 'read'

    @api.multi
    def _compute_website_url(self):
        super(BlogPost, self)._compute_website_url()
        for blog_post in self:
            blog_post.website_url = "/blog/%s/post/%s" % (slug(blog_post.blog_id), slug(blog_post))

    @api.multi
    def _compute_ranking(self):
        res = {}
        for blog_post in self:
            age = datetime.now() - fields.Datetime.from_string(blog_post.post_date)
            res[blog_post.id] = blog_post.visits * (0.5 + random.random()) / max(3, age.days)
        return res

    def _default_content(self):
        return '''  <div class="container">
                        <section class="mt16 mb16">
                            <p class="o_default_snippet_text">''' + _("Start writing here...") + '''</p>
                        </section>
                    </div> '''

    name = fields.Char('Title', required=True, translate=True, default='')
    subtitle = fields.Char('Sub Title', translate=True)
    author_id = fields.Many2one('res.partner', 'Author', default=lambda self: self.env.user.partner_id)
    active = fields.Boolean('Active', default=True)
    cover_properties = fields.Text(
        'Cover Properties',
        default='{"background-image": "none", "background-color": "oe_none", "opacity": "0.6", "resize_class": ""}')
    blog_id = fields.Many2one('blog.blog', 'Blog', required=True, ondelete='cascade')
    tag_ids = fields.Many2many('blog.tag', string='Tags')
    content = fields.Html('Content', default=_default_content, translate=html_translate, sanitize=False)
    teaser = fields.Text('Teaser', compute='_compute_teaser', inverse='_set_teaser')
    teaser_manual = fields.Text(string='Teaser Content')

    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [
            '&', '&', ('model', '=', self._name), ('message_type', '=', 'comment'), ('path', '=', False)
        ],
        string='Website Messages',
        help="Website communication history",
    )
    # creation / update stuff
    create_date = fields.Datetime('Created on', index=True, readonly=True)
    published_date = fields.Datetime('Published Date')
    post_date = fields.Datetime('Published date', compute='_compute_post_date', inverse='_set_post_date', store=True)
    create_uid = fields.Many2one('res.users', 'Created by', index=True, readonly=True)
    write_date = fields.Datetime('Last Modified on', index=True, readonly=True)
    write_uid = fields.Many2one('res.users', 'Last Contributor', index=True, readonly=True)
    author_avatar = fields.Binary(related='author_id.image_small', string="Avatar")
    visits = fields.Integer('No of Views')
    ranking = fields.Float(compute='_compute_ranking', string='Ranking')

    @api.multi
    @api.depends('content', 'teaser_manual')
    def _compute_teaser(self):
        for blog_post in self:
            if blog_post.teaser_manual:
                blog_post.teaser = blog_post.teaser_manual
            else:
                content = html2plaintext(blog_post.content).replace('\n', ' ')
                blog_post.teaser = ' '.join(filter(None, content.split(' '))[:50]) + '...'

    @api.multi
    def _set_teaser(self):
        for blog_post in self:
            blog_post.teaser_manual = blog_post.teaser

    @api.multi
    @api.depends('create_date', 'published_date')
    def _compute_post_date(self):
        for blog_post in self:
            if blog_post.published_date:
                blog_post.post_date = blog_post.published_date
            else:
                blog_post.post_date = blog_post.create_date

    @api.multi
    def _set_post_date(self):
        for blog_post in self:
            blog_post.published_date = blog_post.post_date

    def _check_for_publication(self, vals):
        if vals.get('website_published'):
            for post in self:
                post.blog_id.message_post_with_view(
                    'website_blog.blog_post_template_new_post',
                    subject=post.name,
                    values={'post': post},
                    subtype_id=self.env['ir.model.data'].sudo().xmlid_to_res_id('website_blog.mt_blog_blog_published'))
            return True
        return False

    @api.model
    def create(self, vals):
        post_id = super(BlogPost, self.with_context(mail_create_nolog=True)).create(vals)
        post_id._check_for_publication(vals)
        return post_id

    @api.multi
    def write(self, vals):
        self.ensure_one()
        if 'website_published' in vals and 'published_date' not in vals:
            if self.published_date <= fields.Datetime.now():
                vals['published_date'] = vals['website_published'] and fields.Datetime.now()
        result = super(BlogPost, self).write(vals)
        self._check_for_publication(vals)
        return result

    @api.multi
    def get_access_action(self):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the post on the website directly """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/blog/%s/post/%s' % (self.blog_id.id, self.id),
            'target': 'self',
            'res_id': self.id,
        }

    @api.multi
    def _notification_get_recipient_groups(self, message, recipients):
        """ Override to set the access button: everyone can see an access button
        on their notification email. It will lead on the website view of the
        post. """
        res = super(BlogPost, self)._notification_get_recipient_groups(message, recipients)
        access_action = self._notification_link_helper('view', model=message.model, res_id=message.res_id)
        for category, data in res.iteritems():
            res[category]['button_access'] = {'url': access_action, 'title': _('View Blog Post')}
        return res
