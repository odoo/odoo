# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import api, models, fields, _
from odoo.addons.website.tools import text_from_html
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
        'website.cover_properties.mixin',
        'website.searchable.mixin',
        'web.markup_data.mixin',
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

    @api.depends('blog_post_ids')
    def _compute_blog_post_count(self):
        for record in self:
            record.blog_post_count = len(record.blog_post_ids)

    @api.model
    def _md_blog(
        self,
        *,
        name,
        url,
        description=None,
        image=None,
        posts=None,
    ):
        payload = self._md_payload(
            'Blog',
            name=name,
            url=url,
            description=description,
            image=image,
        )
        if posts:
            payload['blogPost'] = posts
        return payload

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

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        search_fields = ['name']
        fetch_fields = ['id', 'name']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('subtitle')
            fetch_fields.append('subtitle')
            mapping['description'] = {'name': 'subtitle', 'type': 'text', 'match': True}
        return {
            'model': 'blog.blog',
            'base_domain': [website.website_domain()],
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-rss-square',
            'order': 'name desc, id desc' if 'name desc' in order else 'name asc, id desc',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for data in results_data:
            data['url'] = '/blog/%s' % data['id']
        return results_data

    def _get_md(self, website=None):
        self.ensure_one()
        website = website or self.env['website'].get_current_website()
        base_url = website.get_base_url()
        slug = self.env['ir.http']._slug(self)

        description = self.website_meta_description or self.subtitle
        if not description and self.content:
            description = text_from_html(self.content, True)

        return self._md_blog(
            name=self.name,
            url=f'{base_url}/blog/{slug}',
            description=description,
            image=self._md_background_url(website),
        )


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
        'website.cover_properties.mixin', 'website.searchable.mixin', 'web.markup_data.mixin']
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
    tag_ids = fields.Many2many('blog.tag', string='Tags')
    content = fields.Html('Content', default=_default_content, translate=html_translate, sanitize=False)
    teaser = fields.Text('Teaser', compute='_compute_teaser', inverse='_set_teaser', translate=True)
    teaser_manual = fields.Text(string='Teaser Content', translate=True)

    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', '=', 'comment')])

    # creation / update stuff
    create_date = fields.Datetime('Created on', readonly=True)
    published_date = fields.Datetime('Published Date')
    post_date = fields.Datetime('Publishing date', compute='_compute_post_date', inverse='_set_post_date', store=True,
                                help="The blog post will be visible for your visitors as of this date on the website if it is set as published.")
    create_uid = fields.Many2one('res.users', 'Created by', readonly=True)
    write_date = fields.Datetime('Last Updated on', readonly=True)
    write_uid = fields.Many2one('res.users', 'Last Contributor', readonly=True)
    visits = fields.Integer('No of Views', copy=False, default=0, readonly=True)
    website_id = fields.Many2one(related='blog_id.website_id', readonly=True, store=True)

    @api.depends('content', 'teaser_manual')
    def _compute_teaser(self):
        for blog_post in self:
            if blog_post.teaser_manual:
                blog_post.teaser = blog_post.teaser_manual
            else:
                content = text_from_html(blog_post.content, True)
                blog_post.teaser = content[:200] + '...'

    @api.model
    def _md_blog_posting(
        self,
        *,
        headline,
        url,
        main_entity_of_page=None,
        description=None,
        article_body=None,
        image=None,
        date_published=None,
        date_modified=None,
        author=None,
        publisher=None,
        keywords=None,
        article_section=None,
        speakable=None,
        id=None,
        in_language=None,
        is_part_of=None,
        word_count=None,
    ):
        payload = self._md_payload(
            'BlogPosting',
            headline=headline,
            url=url,
            mainEntityOfPage=main_entity_of_page or url,
            description=description,
            articleBody=article_body,
            image=image,
            datePublished=date_published,
            dateModified=date_modified,
            author=author,
            publisher=publisher,
            keywords=keywords,
            articleSection=article_section,
        )
        if speakable:
            payload['speakable'] = speakable
        if id:
            payload['@id'] = id
        if in_language:
            payload['inLanguage'] = in_language
        if is_part_of:
            payload['isPartOf'] = is_part_of
        if word_count:
            payload['wordCount'] = int(word_count)
        return payload

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

    @api.depends('create_date', 'published_date')
    def _compute_post_date(self):
        for blog_post in self:
            if blog_post.published_date:
                blog_post.post_date = blog_post.published_date
            else:
                blog_post.post_date = blog_post.create_date

    def _set_post_date(self):
        for blog_post in self:
            blog_post.published_date = blog_post.post_date
            if not blog_post.published_date:
                blog_post.post_date = blog_post.create_date

    def _check_for_publication(self, vals):
        if vals.get('is_published'):
            for post in self.filtered(lambda p: p.active):
                post.blog_id.message_post_with_source(
                    'website_blog.blog_post_template_new_post',
                    subject=post.name,
                    render_values={'post': post},
                    subtype_xmlid='website_blog.mt_blog_blog_published',
                )
            return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        posts = super(BlogPost, self.with_context(mail_create_nolog=True)).create(vals_list)
        for post, vals in zip(posts, vals_list):
            post._check_for_publication(vals)
        return posts

    def write(self, vals):
        result = True
        # archiving a blog post, unpublished the blog post
        if 'active' in vals and not vals['active']:
            vals['is_published'] = False
        for post in self:
            copy_vals = dict(vals)
            published_in_vals = set(vals.keys()) & {'is_published', 'website_published'}
            if (published_in_vals and 'published_date' not in vals and
                    (not post.published_date or post.published_date <= fields.Datetime.now())):
                copy_vals['published_date'] = vals[list(published_in_vals)[0]] and fields.Datetime.now() or False
            result &= super(BlogPost, post).write(copy_vals)
        self._check_for_publication(vals)
        return result

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
        res['default_opengraph']['article:published_time'] = self.post_date
        res['default_opengraph']['article:modified_time'] = self.write_date
        res['default_opengraph']['article:tag'] = self.tag_ids.mapped('name')
        # background-image might contain single quotes eg `url('/my/url')`
        res['default_opengraph']['og:image'] = json_scriptsafe.loads(self.cover_properties).get('background-image', 'none')[4:-1].strip("'")
        res['default_opengraph']['og:title'] = self.name
        res['default_meta_description'] = self.subtitle
        return res

    def _get_breadcrumb_md(self, website=None):
        self.ensure_one()
        website = website or self.env['website'].get_current_website()
        base_url = website.get_base_url()
        items = [(website.name or base_url, base_url)]
        if self.blog_id:
            slug = self.env['ir.http']._slug(self.blog_id)
            items.append((self.blog_id.name, f'{base_url}/blog/{slug}'))
        items.append((self.name, f'{base_url}{self.website_url}'))
        return self._md_breadcrumb_list(items)

    def _get_md(self, website=None):
        website = website or self.env['website'].get_current_website()
        base_url = website.get_base_url()
        company = website.company_id

        def _truncate_text(text, limit=300):
            if not text:
                return False
            stripped = text.strip()
            if len(stripped) <= limit:
                return stripped
            truncated = stripped[:limit].rsplit(' ', 1)[0].rstrip()
            if not truncated:
                truncated = stripped[:limit].rstrip()
            return f'{truncated}...'

        md = []
        for blog_post in self:
            blog_post_sudo = blog_post.sudo()
            post_url = f'{base_url}{blog_post_sudo.website_url}'
            description = blog_post_sudo.website_meta_description or blog_post_sudo.subtitle or blog_post_sudo.teaser_manual or blog_post_sudo.teaser
            content_text = text_from_html(blog_post_sudo.content, True) if blog_post_sudo.content else False
            truncated_article = _truncate_text(content_text, 300) if content_text else False
            word_count = len(content_text.split()) if content_text else None

            author = False
            if blog_post_sudo.author_id:
                author_partner_sudo = blog_post_sudo.author_id.sudo()
                author = blog_post_sudo._md_person(
                    name=author_partner_sudo.display_name or blog_post_sudo.author_name,
                )

            publisher = False
            if company:
                logo_url = website.image_url(company, 'logo')
                full_logo_url = f'{base_url}{logo_url}' if logo_url else False
                publisher = blog_post_sudo._md_organization(
                    name=company.name,
                    url=base_url,
                    logo=full_logo_url,
                )

            speakable = blog_post_sudo._md_speakable([
                "//h1[contains(@class, 'o_wblog_post_name')]",
                "//div[contains(@class, 'o_wblog_post_subtitle')]",
                "//div[@id='o_wblog_post_content']",
            ])

            post_language = False
            if blog_post_sudo.website_id and blog_post_sudo.website_id.default_lang_id:
                post_language = blog_post_sudo.website_id.default_lang_id.code
            elif website.default_lang_id:
                post_language = website.default_lang_id.code
            if post_language:
                post_language = post_language.replace('_', '-')

            is_part_of = False
            blog = blog_post_sudo.blog_id
            if blog:
                blog_slug = self.env['ir.http']._slug(blog)
                blog_url = f'{base_url}/blog/{blog_slug}'
                is_part_of = blog._md_blog(
                    name=blog.name,
                    url=blog_url,
                    description=blog.subtitle or None,
                    image=blog._md_background_url(website),
                )

            md.append(blog_post_sudo._md_blog_posting(
                headline=blog_post_sudo.name,
                url=post_url,
                description=description,
                article_body=truncated_article,
                image=blog_post_sudo._md_background_url(website),
                date_published=blog_post_sudo._md_datetime(blog_post_sudo.post_date or blog_post_sudo.create_date),
                date_modified=blog_post_sudo._md_datetime(blog_post_sudo.write_date),
                author=author,
                publisher=publisher,
                keywords=', '.join(blog_post_sudo.tag_ids.mapped('name')) if blog_post_sudo.tag_ids else None,
                article_section=blog_post_sudo.blog_id.name if blog_post_sudo.blog_id else None,
                speakable=speakable,
                id=post_url,
                in_language=post_language,
                is_part_of=is_part_of,
                word_count=word_count,
            ))
        return md

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        with_date = options['displayDetail']
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
            domain.append([("post_date", ">=", date_begin), ("post_date", "<=", date_end)])
        if self.env.user.has_group('website.group_website_designer'):
            if state == "published":
                domain.append([("website_published", "=", True), ("post_date", "<=", fields.Datetime.now())])
            elif state == "unpublished":
                domain.append(['|', ("website_published", "=", False), ("post_date", ">", fields.Datetime.now())])
        else:
            domain.append([("post_date", "<=", fields.Datetime.now())])
        search_fields = ['name', 'author_name']
        def search_in_tags(env, search_term):
            tags_like_search = env['blog.tag'].search([('name', 'ilike', search_term)])
            return [('tag_ids', 'in', tags_like_search.ids)]
        fetch_fields = ['name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('content')
            fetch_fields.append('content')
            mapping['description'] = {'name': 'content', 'type': 'text', 'html': True, 'match': True}
        if with_date:
            fetch_fields.append('published_date')
            mapping['detail'] = {'name': 'published_date', 'type': 'date'}
        return {
            'model': 'blog.post',
            'base_domain': domain,
            'search_fields': search_fields,
            'search_extra': search_in_tags,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-rss',
        }
