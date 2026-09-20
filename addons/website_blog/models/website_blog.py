from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import html_escape
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import html_translate

from odoo.addons.base.models.mixin_catalog import name_uniq_index
from odoo.addons.website.tools import text_from_html

_debug = DebugLog(__name__)


class BlogBlog(models.Model):
    _name = "blog.blog"
    _description = "Blog"
    _inherit = [
        "mixin.mail.thread",
        "mixin.website.seo.metadata",
        "mixin.website.multi",
        "mixin.website.cover_properties",
        "mixin.website.searchable",
    ]
    _order = "name"

    _CUSTOMER_HEADERS_LIMIT_COUNT = 0

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    sequence = fields.Integer(default=_default_sequence)
    name = fields.Char(
        string="Blog Name",
        translate=True,
        required=True,
    )
    subtitle = fields.Char(
        string="Blog Subtitle",
        translate=True,
    )
    active = fields.Boolean(default=True)
    content = fields.Html(
        translate=html_translate,
        sanitize=False,
    )
    blog_post_ids = fields.One2many(
        comodel_name="blog.post",
        inverse_name="blog_id",
        string="Blog Posts",
    )
    blog_post_count = fields.Count(
        count_of="blog_post_ids",
        string="Posts",
    )

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals:
            post_ids = (
                self.env["blog.post"]
                .with_context(active_test=False)
                .search([("blog_id", "in", self.ids)])
            )
            _debug.lifecycle(
                "blog_posts_toggled",
                blogs=self,
                posts=len(post_ids),
                active=vals["active"],
            )
            for blog_post in post_ids:
                blog_post.active = vals["active"]
        return res

    def message_post(self, *, parent_id=False, subtype_id=False, **kwargs):
        self.check_singleton()
        if parent_id:
            parent_message = self.env["mail.message"].sudo().browse(parent_id)
            if parent_message.subtype_id and parent_message.subtype_id == self.env.ref(
                "website_blog.mt_blog_blog_published"
            ):
                subtype_id = self.env.ref("mail.mt_note").id
        return super().message_post(
            parent_id=parent_id, subtype_id=subtype_id, **kwargs
        )

    def all_tags(self, join=False, min_limit=1):
        BlogTag = self.env["blog.tag"]
        req = """
            SELECT
                p.blog_id, count(*), r.blog_tag_id
            FROM
                blog_post_blog_tag_rel r
                    join blog_post p on r.blog_post_id=p.id
            WHERE
                p.blog_id = ANY(%s)
            GROUP BY
                p.blog_id,
                r.blog_tag_id
            ORDER BY
                count(*) DESC
        """
        self.env.cr.execute(req, [list(self.ids)])
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

        for blog_id, tag_ids in tag_by_blog.items():
            tag_by_blog[blog_id] = BlogTag.browse(tag_ids)

        return tag_by_blog

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options["displayDescription"]
        search_fields = ["name"]
        fetch_fields = ["id", "name"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "url", "type": "text", "truncate": False},
        }
        if with_description:
            search_fields.append("subtitle")
            fetch_fields.append("subtitle")
            mapping["description"] = {"name": "subtitle", "type": "text", "match": True}
        return {
            "model": "blog.blog",
            "base_domain": [website.website_domain()],
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-rss-square",
            "order": "name desc, id desc"
            if "name desc" in order
            else "name asc, id desc",
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(
            fetch_fields, mapping, icon, limit
        )
        for data in results_data:
            data["url"] = "/blog/%s" % data["id"]
        return results_data


class BlogTagCategory(models.Model):
    _name = "blog.tag.category"
    _description = "Blog Tag Category"
    _order = "name"

    name = fields.Char(
        translate=True,
        required=True,
    )
    tag_ids = fields.One2many(
        comodel_name="blog.tag",
        inverse_name="category_id",
        string="Tags",
    )

    _name_src_uniq = name_uniq_index(
        message="Tag category already exists!",
    )


class BlogTag(models.Model):
    _name = "blog.tag"
    _description = "Blog Tag"
    _inherit = ["mixin.website.seo.metadata"]
    _order = "name"

    name = fields.Char(
        translate=True,
        required=True,
    )
    category_id = fields.Many2one(
        comodel_name="blog.tag.category",
        index=True,
    )
    color = fields.Integer()
    post_ids = fields.Many2many(
        comodel_name="blog.post",
        string="Posts",
    )

    _name_src_uniq = name_uniq_index(
        message="Tag name already exists!",
    )


class BlogPost(models.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = [
        "mixin.mail.thread",
        "mixin.website.seo.metadata",
        "mixin.website.published.multi",
        "mixin.website.page_visibility_options",
        "mixin.website.cover_properties",
        "mixin.website.searchable",
    ]
    _order = "id DESC"
    _mail_post_access = "read"

    def _compute_website_url(self):
        super()._compute_website_url()
        for blog_post in self:
            if blog_post.id:
                blog_post.website_url = "/blog/%s/%s" % (
                    self.env["ir.http"]._slug(blog_post.blog_id),
                    self.env["ir.http"]._slug(blog_post),
                )

    def _default_content(self):
        text = html_escape(_("Start writing here..."))
        return """
            <p>%(text)s</p>
        """ % {"text": text}

    name = fields.Char(
        string="Title",
        translate=True,
        default="",
        required=True,
    )
    subtitle = fields.Char(
        string="Sub Title",
        translate=True,
    )
    author_id = fields.Many2one(
        comodel_name="res.partner",
        default=lambda self: self.env.user.partner_id,
        index="btree_not_null",
    )
    author_avatar = fields.Binary(
        related="author_id.image_128",
        string="Avatar",
        readonly=False,
    )
    author_name = fields.Char(  # noqa: E8529  the website search matches on it in SQL, and display_name has no column to join
        related="author_id.display_name",
        string="Author Name",
        store=True,
        readonly=False,
    )
    active = fields.Boolean(default=True)
    blog_id = fields.Many2one(
        comodel_name="blog.blog",
        default=lambda self: self.env["blog.blog"].search([], limit=1),
        index=True,
        required=True,
        ondelete="cascade",
    )
    tag_ids = fields.Many2many(
        comodel_name="blog.tag",
        string="Tags",
    )
    content = fields.Html(
        translate=html_translate,
        sanitize=False,
        default=_default_content,
    )
    teaser = fields.Text(
        translate=True,
        compute="_compute_teaser",
        inverse="_inverse_teaser",
    )
    teaser_manual = fields.Text(
        string="Teaser Content",
        translate=True,
    )

    website_message_ids = fields.One2many(
        domain=lambda self: [
            ("model", "=", self._name),
            ("message_type", "=", "comment"),
        ]
    )

    create_date = fields.Datetime(
        string="Created on",
        readonly=True,
    )
    published_date = fields.Datetime()
    post_date = fields.Datetime(
        string="Publishing date",
        compute="_compute_post_date",
        inverse="_inverse_post_date",
        store=True,
        help="The blog post will be visible for your visitors as of this date on the website if it is set as published.",
    )
    create_uid = fields.Many2one(
        comodel_name="res.users",
        string="Created by",
        readonly=True,
    )
    write_date = fields.Datetime(
        string="Last Updated on",
        readonly=True,
    )
    write_uid = fields.Many2one(
        comodel_name="res.users",
        string="Last Contributor",
        readonly=True,
    )
    visits = fields.Integer(
        string="No of Views",
        default=0,
        copy=False,
        readonly=True,
    )
    website_id = fields.Many2one(
        related="blog_id.website_id",
        readonly=True,
    )

    @api.depends("content", "teaser_manual")
    def _compute_teaser(self):
        for blog_post in self:
            if blog_post.teaser_manual:
                blog_post.teaser = blog_post.teaser_manual
            else:
                content = text_from_html(blog_post.content, True)
                blog_post.teaser = content[:200] + "..."

    def _inverse_teaser(self):
        for blog_post in self:
            if not blog_post.with_context(lang="en_US").teaser_manual:
                blog_post.update_field_translations("teaser_manual", {"en_US": ""})
            blog_post.teaser_manual = blog_post.teaser

    @api.depends("create_date", "published_date")
    def _compute_post_date(self):
        for blog_post in self:
            if blog_post.published_date:
                blog_post.post_date = blog_post.published_date
            else:
                blog_post.post_date = blog_post.create_date

    def _inverse_post_date(self):
        for blog_post in self:
            blog_post.published_date = blog_post.post_date
            if not blog_post.published_date:
                blog_post.post_date = blog_post.create_date

    def _check_for_publication(self, vals):
        if vals.get("is_published"):
            active_posts = self.filtered(lambda p: p.active)
            for post in active_posts:
                post.blog_id.message_post_with_source(
                    "website_blog.blog_post_template_new_post",
                    subject=post.name,
                    render_values={"post": post},
                    subtype_xmlid="website_blog.mt_blog_blog_published",
                )
            _debug.lifecycle("blog_posts_published", posts=active_posts)
            return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        posts = super(BlogPost, self.with_context(mail_create_nolog=True)).create(
            vals_list
        )
        _debug.lifecycle("create", posts=posts, count=len(posts))
        for post, vals in zip(posts, vals_list, strict=True):
            post._check_for_publication(vals)
        return posts

    def write(self, vals):
        result = True
        _debug.lifecycle("write", posts=self, count=len(self), fields=sorted(vals))
        if "active" in vals and not vals["active"]:
            _debug.logic("blog_post_unpublished", reason="archived", posts=self)
            vals["is_published"] = False
        for post in self:
            copy_vals = dict(vals)
            published_in_vals = set(vals.keys()) & {"is_published", "website_published"}
            if (
                published_in_vals
                and "published_date" not in vals
                and (
                    not post.published_date
                    or post.published_date <= fields.Datetime.now()
                )
            ):
                _debug.lifecycle(
                    "blog_post_published_date_set",
                    post=post.id,
                    by=sorted(published_in_vals),
                )
                copy_vals["published_date"] = (
                    vals[next(iter(published_in_vals))] and fields.Datetime.now()
                ) or False
            result &= super(BlogPost, post).write(copy_vals)
        self._check_for_publication(vals)
        return result

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", blog.name))
            for blog, vals in zip(self, vals_list, strict=True)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def _get_access_action(self, access_uid=None, force_website=False):
        self.check_singleton()
        user = (
            self.env["res.users"].sudo().browse(access_uid)
            if access_uid
            else self.env.user
        )
        if not force_website and user.share and not self.sudo().website_published:
            return super()._get_access_action(
                access_uid=access_uid, force_website=force_website
            )
        return {
            "type": "ir.actions.act_url",
            "url": self.website_url,
            "target": "self",
            "target_type": "public",
            "res_id": self.id,
        }

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.check_singleton()
        if self.website_published:
            for _group_name, _group_method, group_data in groups:
                group_data["has_button_access"] = True

        return groups

    def _notify_thread_by_inbox(
        self, message, recipients_data, msg_vals=False, **kwargs
    ):
        msg_vals = msg_vals or {}
        if msg_vals.get("message_type", message.message_type) == "comment":
            return None
        return super()._notify_thread_by_inbox(
            message, recipients_data, msg_vals=msg_vals, **kwargs
        )

    def _get_default_website_meta(self):
        res = super()._get_default_website_meta()
        res["default_opengraph"]["og:description"] = res["default_twitter"][
            "twitter:description"
        ] = self.subtitle
        res["default_opengraph"]["og:type"] = "article"
        res["default_opengraph"]["article:published_time"] = self.post_date
        res["default_opengraph"]["article:modified_time"] = self.write_date
        res["default_opengraph"]["article:tag"] = self.tag_ids.mapped("name")
        res["default_opengraph"]["og:image"] = res["default_twitter"][
            "twitter:image"
        ] = (
            json_scriptsafe.loads(self.cover_properties)
            .get("background-image", "none")[4:-1]
            .strip("'")
        )
        res["default_opengraph"]["og:title"] = res["default_twitter"][
            "twitter:title"
        ] = self.name
        res["default_meta_description"] = self.subtitle
        return res

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options["displayDescription"]
        with_date = options["displayDetail"]
        blog = options.get("blog")
        tags = options.get("tag")
        date_begin = options.get("date_begin")
        date_end = options.get("date_end")
        state = options.get("state")
        domain = [website.website_domain()]
        if blog:
            domain.append([("blog_id", "=", self.env["ir.http"]._unslug(blog)[1])])
        if tags:
            active_tag_ids = [
                self.env["ir.http"]._unslug(tag)[1] for tag in tags.split(",")
            ] or []
            if active_tag_ids:
                domain.append([("tag_ids", "in", active_tag_ids)])
        if date_begin and date_end:
            domain.append(
                [("post_date", ">=", date_begin), ("post_date", "<=", date_end)]
            )
        if self.env.user.has_group("website.group_website_designer"):
            if state == "published":
                domain.append(
                    [
                        ("website_published", "=", True),
                        ("post_date", "<=", fields.Datetime.now()),
                    ]
                )
            elif state == "unpublished":
                domain.append(
                    [
                        "|",
                        ("website_published", "=", False),
                        ("post_date", ">", fields.Datetime.now()),
                    ]
                )
        else:
            domain.append([("post_date", "<=", fields.Datetime.now())])
        search_fields = ["name", "author_name"]

        def search_in_tags(env, search_term):
            tags_like_search = env["blog.tag"].search([("name", "ilike", search_term)])
            return [("tag_ids", "in", tags_like_search.ids)]

        fetch_fields = ["name", "website_url"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "website_url", "type": "text", "truncate": False},
        }
        if with_description:
            search_fields.append("content")
            fetch_fields.append("content")
            mapping["description"] = {
                "name": "content",
                "type": "text",
                "html": True,
                "match": True,
            }
        if with_date:
            fetch_fields.append("published_date")
            mapping["detail"] = {"name": "published_date", "type": "date"}
        return {
            "model": "blog.post",
            "base_domain": domain,
            "search_fields": search_fields,
            "search_extra": search_in_tags,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-rss",
        }
