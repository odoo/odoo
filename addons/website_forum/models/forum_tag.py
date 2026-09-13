from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ForumTag(models.Model):
    _name = "forum.tag"
    _description = "Forum Tag"
    _inherit = [
        "mixin.mail.thread",
        "mixin.website.searchable",
        "mixin.website.seo.metadata",
    ]

    name = fields.Char(required=True)
    color = fields.Integer()
    forum_id = fields.Many2one(
        comodel_name="forum.forum",
        index=True,
        required=True,
    )
    post_ids = fields.Many2many(
        comodel_name="forum.post",
        relation="forum_tag_rel",
        column1="forum_tag_id",
        column2="forum_post_id",
        string="Posts",
        domain=[("state", "=", "active")],
    )
    posts_count = fields.Count(
        count_of="post_ids",
        string="Number of Posts",
        store=True,
    )
    website_url = fields.Char(
        string="Link to questions with the tag",
        compute="_compute_website_url",
    )
    _name_uniq = models.Constraint(
        "unique (name, forum_id)",
        "Tag name already exists!",
    )

    @api.depends("forum_id", "forum_id.name", "name")
    def _compute_website_url(self):
        for tag in self:
            tag.website_url = f"/forum/{self.env['ir.http']._slug(tag.forum_id)}/tag/{self.env['ir.http']._slug(tag)}/questions"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            forum = self.env["forum.forum"].browse(vals.get("forum_id"))
            if self.env.user.karma < forum.karma_tag_create and not self.env.is_admin():
                raise AccessError(
                    _("%d karma required to create a new Tag.", forum.karma_tag_create)
                )
        return super(
            ForumTag,
            self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True),
        ).create(vals_list)

    @api.model
    def _search_get_detail(self, website, order, options):
        search_fields = ["name"]
        fetch_fields = ["id", "name", "website_url"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "website_url", "type": "text", "truncate": False},
        }
        base_domain = []
        if forum := options.get("forum"):
            forum_ids = (
                (self.env["ir.http"]._unslug(forum)[1],)
                if isinstance(forum, str)
                else forum.ids
            )
            search_domain = options.get("domain")
            base_domain = [
                search_domain
                if search_domain is not None
                else [("forum_id", "in", forum_ids)]
            ]
        return {
            "model": "forum.tag",
            "base_domain": base_domain,
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-tag",
            "order": ",".join(
                filter(lambda f: "is_published" not in f, order.split(","))
            ),
        }
