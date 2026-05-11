# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import random

from odoo import api, models, fields, _
from odoo.addons.website.tools import images_from_html, text_from_html
from odoo.addons.website.helpers.jsonld_builder import JsonLd
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import html_translate
from odoo.tools import html_escape


class BlogBlog(models.Model):
    _name = 'blog.blog'
    _description = 'Blog'
    _inherit = [
        'mail.thread',
        'website.seo.metadata',
        'website.multi.mixin',
        'website.located.mixin',
        'website.cover_properties.mixin',
        'website.searchable.mixin',
        'website.structured_data.mixin',
    ]
    _order = 'name'

    _CUSTOMER_HEADERS_LIMIT_COUNT = 0  # never use X-Msg-To headers

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    sequence = fields.Integer("Sequence", default=_default_sequence)
    name = fields.Char('Blog Name', required=True, translate=True)
    subtitle = fields.Char('Blog Subtitle', translate=True)
    active = fields.Boolean('Active', default=True)
    content = fields.Html('Content', translate=html_translate, sanitize=False)
    blog_post_ids = fields.One2many('blog.post', 'blog_id', 'Blog Posts')
    blog_post_count = fields.Integer("Posts", compute='_compute_blog_post_count')

    def _compute_website_url(self):
        super()._compute_website_url()
        for record in self:
            if record.id:
                record.website_url = '/blog/%s' % self.env['ir.http']._slug(record)

    @api.depends('blog_post_ids')
    def _compute_blog_post_count(self):
        for record in self:
            record.blog_post_count = len(record.blog_post_ids)

    def write(self, vals):
        res = super().write(vals)
        if 'active' in vals:
            # archiving/unarchiving a blog does it on its posts, too
            post_ids = self.env['blog.post'].with_context(active_test=False).search([
                ('blog_id', 'in', self.ids)
            ])
            for blog_post in post_ids:
                blog_post.active = vals['active']
        return res

    def message_post(self, *, parent_id=False, subtype_id=False, **kwargs):
        """ Temporary workaround to avoid spam. If someone replies on a channel
        through the 'Presentation Published' email, it should be considered as a
        note as we don't want all channel followers to be notified of this answer. """
        self.ensure_one()
        if parent_id:
            parent_message = self.env['mail.message'].sudo().browse(parent_id)
            if parent_message.subtype_id and parent_message.subtype_id == self.env.ref('website_blog.mt_blog_blog_published'):
                subtype_id = self.env.ref('mail.mt_note').id
        return super().message_post(parent_id=parent_id, subtype_id=subtype_id, **kwargs)

    def all_tags(self, join=False, min_limit=1):
        BlogTag = self.env['blog.tag']
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
        tag_by_blog = {i.id: [] for i in self}
        all_tags = set()
        for blog_id, freq, tag_id in self.env.cr.fetchall():
            if freq >= min_limit:
                if join:
                    all_tags.add(tag_id)
                else:
                    tag_by_blog[blog_id].append(tag_id)

        if join:
            return BlogTag.browse(all_tags)

        for blog_id in tag_by_blog:
            tag_by_blog[blog_id] = BlogTag.browse(tag_by_blog[blog_id])

        return tag_by_blog

    def _get_breadcrumb_items(self, is_detail_page=False):
        """Return breadcrumb items for a blog page."""
        items = super()._get_breadcrumb_items(is_detail_page)
        items.append((self.env._('Blog Posts'), "/blog"))
        if is_detail_page:
            items.append((self.name, self.website_url))
        return items

    def _build_blog_jsonld(self):
        """Build the base ``Blog`` schema."""
        self.ensure_one()
        base_url = self.get_base_url()
        blog_slug = self.env["ir.http"]._slug(self)
        blog_url = f"{base_url}/blog/{blog_slug}"
        schema_data = {
            "@id": f"{blog_url}/#blog",
            "name": self.name,
            "url": blog_url,
        }
        if self.subtitle:
            schema_data["description"] = self.subtitle
        nested_schema_data = {
            "publisher": JsonLd("Organization", {"@id": f"{base_url}/#organization"}),
        }
        return JsonLd("Blog", schema_data).add_nested(nested_schema_data)


class BlogTagCategory(models.Model):
    _name = 'blog.tag.category'
    _description = 'Blog Tag Category'
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    tag_ids = fields.One2many('blog.tag', 'category_id', string='Tags')

    _name_uniq = models.Constraint(
        'unique (name)',
        'Tag category already exists!',
    )


class BlogTag(models.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    category_id = fields.Many2one('blog.tag.category', 'Category', index=True)
    color = fields.Integer('Color')
    post_ids = fields.Many2many('blog.post', string='Posts')

    _name_uniq = models.Constraint(
        'unique (name)',
        'Tag name already exists!',
    )


class BlogPost(models.Model):
    _name = 'blog.post'
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.multi.mixin',
        'website.page_visibility_options.mixin',
        'website.cover_properties.mixin', 'website.searchable.mixin',
        'website.structured_data.mixin']
    _order = 'id DESC'
    _mail_post_access = 'read'

    def _compute_website_url(self):
        super(BlogPost, self)._compute_website_url()
        for blog_post in self:
            if blog_post.id:
                blog_post.website_url = "/blog/%s/%s" % (self.env['ir.http']._slug(blog_post.blog_id), self.env['ir.http']._slug(blog_post))

    def _default_content(self):
        text = html_escape(_("Start writing here..."))
        return """
            <p>%(text)s</p>
        """ % {"text": text}
    name = fields.Char('Title', required=True, translate=True, default='')
    subtitle = fields.Char('Sub Title', translate=True)
    author_id = fields.Many2one('res.partner', 'Author', default=lambda self: self.env.user.partner_id, index='btree_not_null')
    author_avatar = fields.Binary(related='author_id.image_128', string="Avatar", readonly=False)
    author_name = fields.Char(related='author_id.display_name', string="Author Name", readonly=False, store=True)
    active = fields.Boolean('Active', default=True)
    blog_id = fields.Many2one('blog.blog', 'Blog', required=True, index=True, ondelete='cascade', default=lambda self: self.env['blog.blog'].search([], limit=1))
    recommended_next_post_id = fields.Many2one('blog.post', string="Recommended Next Post",
        help="Next blog post that will be shown as the next article to users at the bottom of the blog post.")
    tag_ids = fields.Many2many('blog.tag', string='Tags')
    content = fields.Html('Content', default=_default_content, translate=html_translate, sanitize=False)
    teaser = fields.Text('Teaser', compute='_compute_teaser', inverse='_set_teaser', translate=True)
    teaser_manual = fields.Text(string='Teaser Content', translate=True)

    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', '=', 'comment')])

    # creation / update stuff
    create_date = fields.Datetime('Created on', readonly=True)
    create_uid = fields.Many2one('res.users', 'Created by', readonly=True)
    write_date = fields.Datetime('Last Updated on', readonly=True)
    write_uid = fields.Many2one('res.users', 'Last Contributor', readonly=True)
    visits = fields.Integer('No of Views', copy=False, default=0, readonly=True)
    website_id = fields.Many2one(related='blog_id.website_id', readonly=True, store=True)

    def _build_blog_post_base_jsonld(self):
        """Build the base ``BlogPosting`` schema."""
        self.ensure_one()
        website = self.env['website'].get_current_website()
        base_url = self.get_base_url()
        post_url = f"{base_url}{self.website_url}"
        schema_data = {
            "@id": f"{post_url}/#blogpost",
            "headline": self.name,
            "url": post_url,
            "datePublished": JsonLd.to_iso_datetime(self.published_date),
            "dateModified": JsonLd.to_iso_datetime(self.write_date),
        }
        if tags := self.tag_ids.mapped("name"):
            schema_data["keywords"] = ", ".join(tags)
        if website.is_view_active('website_blog.opt_posts_loop_show_teaser') and self.teaser:
            schema_data["description"] = self.teaser
        if website.is_view_active('website_blog.opt_posts_loop_show_stats') and self.website_message_ids:
            schema_data["commentCount"] = len(self.website_message_ids)
        nested_schema_data = {}
        if (
            website.is_view_active('website_blog.opt_posts_loop_show_cover')
            and (image_url := self._get_image_url())
        ):
            nested_schema_data["image"] = JsonLd("ImageObject", {"url": base_url + image_url})
        organization = JsonLd("Organization", {"@id": f"{base_url}/#organization"})
        nested_schema_data["publisher"] = organization
        author_sudo = self.author_id.sudo()
        if author_sudo.is_company:
            nested_schema_data["author"] = organization
        else:
            nested_schema_data["author"] = JsonLd("Person", {"name": author_sudo.display_name})
        blog_slug = self.env['ir.http']._slug(self.blog_id)
        nested_schema_data["isPartOf"] = JsonLd("Blog", {"@id": f"{base_url}/blog/{blog_slug}/#blog"})
        return JsonLd("BlogPosting", schema_data).add_nested(nested_schema_data)

    def _get_breadcrumb_items(self, is_detail_page=False):
        """Return breadcrumb items for a blog post page."""
        if is_detail_page:
            blog = self.blog_id
        else:
            blog = self.blog_id.browse(self.env.context.get('blog_id'))
        items = blog._get_breadcrumb_items(bool(blog))
        if is_detail_page:
            items.append((self.name, self.website_url))
        return items

    def _build_blog_post_jsonld(self):
        """Build the full ``BlogPosting`` schema for a post detail page."""
        self.ensure_one()
        website = self.env['website'].get_current_website()
        base_url = website.get_base_url()
        blog_post_jsonld = self._build_blog_post_base_jsonld()
        image_urls = []
        if not blog_post_jsonld.get("image"):
            if image_url := self._get_image_url():
                image_urls.append(f"{base_url}{image_url}")
        if html_images := images_from_html(self.content, base_url):
            image_urls.extend(dict.fromkeys(html_images))
        schema_data = {}
        if (
            not blog_post_jsonld.get("commentCount")
            and website.is_view_active('website_blog.opt_blog_post_comment')
        ):
            schema_data["commentCount"] = len(self.website_message_ids)
        if self.env.lang:
            schema_data["inLanguage"] = self.env.lang.replace("_", "-")
        if self.content:
            if content_text := text_from_html(self.content, True):
                schema_data["wordCount"] = len(content_text.split())
        if schema_data:
            blog_post_jsonld.set(schema_data)
        if image_urls:
            blog_post_jsonld.add_nested({
                "image": [
                    JsonLd("ImageObject", {"url": url})
                    for url in image_urls
                ],
            })
        return blog_post_jsonld

    def _get_jsonld(self, is_detail_page=False):
        """Return the list of JsonLd schemas for blog post."""
        schemas = super()._get_jsonld(is_detail_page)
        if is_detail_page:
            schemas.extend([
                self.blog_id._build_blog_jsonld(),
                self._build_blog_post_jsonld(),
            ])
            return schemas
        current_blog = self.env['blog.blog'].browse(self.env.context.get('blog_id')).exists()
        blogs = current_blog or self.mapped('blog_id')
        for blog_record in blogs:
            schemas.append(blog_record._build_blog_jsonld())
        schemas.append(self._build_blog_collectionpage_jsonld(blog=current_blog))
        return schemas

    def _build_blog_collectionpage_jsonld(self, blog=None):
        """Build a ``CollectionPage`` schema for the blog listing page."""
        website = self.env['website'].get_current_website()
        base_url = website.get_base_url()
        collectionpage_name = f"{blog.name}" if blog else self.env._('Blog Posts')
        haspart_jsonld = [post._build_blog_post_base_jsonld() for post in self]
        organization_jsonld = JsonLd("Organization", {"@id": f"{base_url}/#organization"})
        return JsonLd("CollectionPage", {
            "name": collectionpage_name,
            "url": f"{base_url}/blog",
        }).add_nested({"hasPart": haspart_jsonld, "isPartOf": organization_jsonld})

    @api.depends('content', 'teaser_manual')
    def _compute_teaser(self):
        for blog_post in self:
            if blog_post.teaser_manual:
                blog_post.teaser = blog_post.teaser_manual
            else:
                content = text_from_html(blog_post.content, True)
                blog_post.teaser = content[:200] + '...'

    def _set_teaser(self):
        for blog_post in self:
            if not blog_post.with_context(lang='en_US').teaser_manual:
                # By default, if no teaser is set in english, it will use the
                # first 200 characters of the content. We don't want to break
                # that when adding a manual teaser in a translation.
                # That's how the ORM work: when setting a translation value, if
                # there is no source value, the source will also receive the
                # translation value
                blog_post.update_field_translations('teaser_manual', {'en_US': ''})
            blog_post.teaser_manual = blog_post.teaser

    def _check_for_action_post_publish(self):
        """Send notification when a post goes live for the first time."""
        self.ensure_one()
        force_publish = self.env.context.get('force_website_published')
        if (force_publish or self.website_published) and self.active and not self.published_date:
            return self.blog_id.message_post_with_source(
                'website_blog.blog_post_template_new_post',
                subject=self.name,
                render_values={'post': self},
                subtype_xmlid='website_blog.mt_blog_blog_published',
            )
        return self.env['mail.message']

    @api.model_create_multi
    def create(self, vals_list):
        return super(BlogPost, self.with_context(mail_create_nolog=True)).create(vals_list)

    def write(self, vals):
        new_vals = dict(vals)
        if new_vals.get('active') is False:
            new_vals['is_published'] = False
        return super().write(new_vals)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", blog.name)) for blog, vals in zip(self, vals_list)]

    def _get_access_action(self, access_uid=None, force_website=False):
        """ Instead of the classic form view, redirect to the post on website
        directly if user is an employee or if the post is published. """
        self.ensure_one()
        user = self.env['res.users'].sudo().browse(access_uid) if access_uid else self.env.user
        if not force_website and user.share and not self.sudo().website_published:
            return super(BlogPost, self)._get_access_action(access_uid=access_uid, force_website=force_website)
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
            'target_type': 'public',
            'res_id': self.id,
        }

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()
        if self.website_published:
            for _group_name, _group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    def _notify_thread_by_inbox(self, message, recipients_data, msg_vals=False, **kwargs):
        # Override to avoid keeping all notified recipients of a comment.
        # We avoid tracking needaction on post comments. Only emails should be
        # sufficient.
        msg_vals = msg_vals or {}
        if msg_vals.get('message_type', message.message_type) == 'comment':
            return
        return super(BlogPost, self)._notify_thread_by_inbox(message, recipients_data, msg_vals=msg_vals, **kwargs)

    def _default_website_meta(self):
        res = super(BlogPost, self)._default_website_meta()
        res['default_opengraph']['og:description'] = self.subtitle
        res['default_opengraph']['og:type'] = 'article'
        res['default_opengraph']['article:published_time'] = self.published_date
        res['default_opengraph']['article:modified_time'] = self.write_date
        res['default_opengraph']['article:tag'] = self.tag_ids.mapped('name')
        # background-image might contain single quotes eg `url('/my/url')`
        res['default_opengraph']['og:image'] = json_scriptsafe.loads(self.cover_properties).get('background-image', 'none')[4:-1].strip("\"'")
        res['default_opengraph']['og:title'] = self.name
        res['default_meta_description'] = self.subtitle
        return res

    @api.model
    def _search_get_detail(self, website, order, options):
        blog = options.get('blog')
        tags = options.get('tag')
        date_begin = options.get('date_begin')
        date_end = options.get('date_end')
        state = options.get('state')
        domain = [website.website_domain()]
        if blog:
            domain.append([('blog_id', '=', self.env['ir.http']._unslug(blog)[1])])
        if tags:
            active_tag_ids = [self.env['ir.http']._unslug(tag)[1] for tag in tags.split(',')] or []
            if active_tag_ids:
                domain.append([('tag_ids', 'in', active_tag_ids)])
        if date_begin and date_end:
            domain.append([("published_date", ">=", date_begin), ("published_date", "<=", date_end)])
        if self.env.user.has_group('website.group_website_designer'):
            if state == "published":
                domain.append([("website_published", "=", True)])
            elif state == "unpublished":
                domain.append([("website_published", "=", False), ("publish_on", "=", False)])
            elif state == "scheduled":
                domain.append([("publish_on", "!=", False)])
        else:
            domain.append([("website_published", "=", True)])
        search_fields = ['name', 'author_name', 'tag_ids.name', 'content']
        fetch_fields = ['name', 'website_url', 'author_name', 'content']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
            'search_item_metadata': {'name': 'author_name', 'type': 'text', 'match': True},
            'image_url': {'name': 'image_url', 'type': 'html'},
            'tags': {'name': 'tag_ids', 'type': 'tags', 'match': True},
            'description': {'name': 'content', 'type': 'text', 'html': True, 'match': True},
        }
        return {
            'model': 'blog.post',
            'base_domain': domain,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-rss',
            'group_name': self.env._("Blog Articles"),
            'sequence': 60,
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for post, data in zip(self, results_data):
            data['tag_ids'] = post.tag_ids.read(['name'])
            data['image_url'] = post._get_image_url()
        return results_data
