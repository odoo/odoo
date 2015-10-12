# -*- coding: utf-8 -*-
import lxml
import random

from odoo import api, fields, models, _
from odoo.addons.website.models.website import slug


class Blog(models.Model):
    _name = 'blog.blog'
    _description = 'Blogs'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'name'

    name = fields.Char('Blog Name', required=True, translate=True)
    subtitle = fields.Char('Blog Subtitle', translate=True)

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
        self.env.cr.execute(req, [tuple(self.ids)])
        tag_by_blog = {i: [] for i in self.ids}
        for blog_id, freq, tag_id in self.env.cr.fetchall():
            if freq >= min_limit:
                tag_by_blog[blog_id].append(tag_id)

        Tag = self.env['blog.tag']
        for blog_id in tag_by_blog:
            tag_by_blog[blog_id] = Tag.browse(tag_by_blog[blog_id])
        return tag_by_blog


class BlogTag(models.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    post_ids = fields.Many2many('blog.post', string="Posts")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class BlogPost(models.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin']
    _order = 'id DESC'
    _mail_post_access = 'read'

    def _default_content(self):
        return '''  <div class="container">
                        <section class="mt16 mb16">
                            <p class="o_default_snippet_text">''' + _("Start writing here...") + '''</p>
                        </section>
                    </div> '''

    name = fields.Char(string='Title', required=True, translate=True, default='')
    subtitle = fields.Char(string='Sub Title', translate=True, default=_('Subtitle'))
    author_id = fields.Many2one('res.partner', string='Author', default=lambda self: self.env.user.partner_id)
    cover_properties = fields.Text(string='Cover Properties', default='{"background-image": "none", "background-color": "oe_none", "opacity": "0.6", "resize_class": ""}')
    blog_id = fields.Many2one(
        'blog.blog', string='Blog',
        required=True, ondelete='cascade'
    )
    tag_ids = fields.Many2many(
        'blog.tag', string='Tags'
    )
    content = fields.Html(string='Content', translate=True, sanitize=False, default=_default_content)
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [
            '&', '&', ('model', '=', self._name), ('message_type', '=', 'comment'), ('path', '=', False)
        ],
        string='Website Messages',
        help="Website communication history"
    )
    author_avatar = fields.Binary(related="author_id.image_small", string="Avatar")
    visits = fields.Integer(string='No of Views')

    @api.model
    def create(self, vals):
        if 'content' in vals and vals['content']:
            vals['content'], mapping = self.html_tag_nodes(vals['content'], attribute='data-chatter-id', tags=['p'])
        post = super(BlogPost, self.with_context(mail_create_nolog=True)).create(vals)
        post._check_for_publication(vals)
        return post

    @api.multi
    def write(self, vals):
        if 'content' in vals and vals['content']:
            vals['content'], mapping = self.html_tag_nodes(vals['content'], attribute='data-chatter-id', tags=['p'])
            existing = [x[0] for x in mapping if x[0]]
            self.website_message_ids.filtered(lambda message: message.path not in existing and message.path).unlink()
        result = super(BlogPost, self).write(vals)
        self._check_for_publication(vals)
        return result

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(BlogPost, self)._website_url(field_name, arg)
        res.update({(blog_post.id, '/blog/%s/post/%s' % (slug(blog_post.blog_id), slug(blog_post))) for blog_post in self})
        return res

    @api.model
    def html_tag_nodes(self, html, attribute=None, tags=None):
        """ Processing of html content to tag paragraphs and set them an unique
        ID.
        :return result: (html, mappin), where html is the updated html with ID
                        and mapping is a list of (old_ID, new_ID), where old_ID
                        is None is the paragraph is a new one. """

        existing_attributes = []
        mapping = []
        if not html:
            return html, mapping
        if tags is None:
            tags = ['p']
        if attribute is None:
            attribute = 'data-unique-id'

        # form a tree
        root = lxml.html.fragment_fromstring(html, create_parent='div')
        if not len(root) and root.text is None and root.tail is None:
            return html, mapping

        # check all nodes, replace :
        # - img src -> check URL
        # - a href -> check URL
        for node in root.iter():
            if node.tag not in tags:
                continue
            ancestor_tags = [parent.tag for parent in node.iterancestors()]

            old_attribute = node.get(attribute)
            new_attribute = old_attribute
            if not new_attribute or (old_attribute in existing_attributes):
                if ancestor_tags:
                    ancestor_tags.pop()
                counter = random.randint(10000, 99999)
                ancestor_tags.append('counter_%s' % counter)
                new_attribute = '/'.join(reversed(ancestor_tags))
                node.set(attribute, new_attribute)

            existing_attributes.append(new_attribute)
            mapping.append((old_attribute, new_attribute))

        html = lxml.html.tostring(root, pretty_print=False, method='html')
        # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
        if html.startswith('<div>') and html.endswith('</div>'):
            html = html[5:-6]
        return html, mapping

    @api.multi
    def _check_for_publication(self, vals):
        if vals.get('website_published'):
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            for post in self:
                post.blog_id.message_post(
                    body='<p>%(post_publication)s <a href="%(base_url)s/blog/%(blog_slug)s/post/%(post_slug)s">%(post_link)s</a></p>' % {
                        'post_publication': _('A new post %s has been published on the %s blog.') % (post.name, post.blog_id.name),
                        'post_link': _('Click here to access the post.'),
                        'base_url': base_url,
                        'blog_slug': slug(post.blog_id),
                        'post_slug': slug(post),
                    },
                    subtype='website_blog.mt_blog_blog_published')
            return True
        return False

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


class Website(models.Model):
    _inherit = "website"

    @api.model
    def page_search_dependencies(self, view_id):
        dep = super(Website, self).page_search_dependencies(view_id)
        view = self.env['ir.ui.view'].browse(view_id)
        name = view.key.replace("website.", "")
        fullname = "website.%s" % name

        dom = [
            '|', ('content', 'ilike', '/page/%s' % name), ('content', 'ilike', '/page/%s' % fullname)
        ]
        posts = self.env['blog.post'].search(dom)
        if posts:
            page_key = _('Blog Post')
            dep[page_key] = []
        for post in posts:
            dep[page_key].append({
                'text': _('Blog Post <b>%s</b> seems to have a link to this page !' % post.name),
                'link': post.website_url
            })

        return dep
