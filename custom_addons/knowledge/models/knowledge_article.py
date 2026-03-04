from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class KnowledgeArticle(models.Model):
    _name = "knowledge.article"
    _description = "Knowledge Article"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _parent_name = "parent_id"
    _parent_store = True
    _order = "sequence, id"

    name = fields.Char(required=True, tracking=True)
    body = fields.Html(default="<p><br></p>", sanitize=False, tracking=True)
    parent_id = fields.Many2one("knowledge.article", index=True, ondelete="restrict")
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("knowledge.article", "parent_id")
    root_article_id = fields.Many2one(
        "knowledge.article",
        compute="_compute_root_article_id",
        store=True,
        index=True,
        recursive=True,
    )
    user_can_write = fields.Boolean(compute="_compute_user_flags")
    user_has_access = fields.Boolean(compute="_compute_user_flags")
    member_ids = fields.One2many("knowledge.article.member", "article_id")
    favorite_ids = fields.One2many("knowledge.article.favorite", "article_id")
    is_favorited = fields.Boolean(compute="_compute_is_favorited")
    favorite_count = fields.Integer(compute="_compute_favorite_count")
    icon = fields.Char()
    cover_image_id = fields.Many2one("knowledge.cover", ondelete="set null")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [("workspace", "Workspace"), ("private", "Private"), ("shared", "Shared")],
        required=True,
        default="workspace",
        index=True,
    )
    last_edition_date = fields.Datetime(readonly=True)
    last_edition_uid = fields.Many2one("res.users", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete="restrict",
    )
    owner_partner_id = fields.Many2one(
        "res.partner",
        required=True,
        default=lambda self: self.env.user.partner_id,
        index=True,
        ondelete="restrict",
    )
    is_locked = fields.Boolean(default=False, tracking=True)

    _knowledge_article_name_parent_company_uniq = models.Constraint(
        "unique(name, parent_id, company_id)",
        "An article with the same title already exists in this location.",
    )

    # -- GOV INTEGRATION NOTE -------------------------------------------------
    # Knowledge articles can serve as process documentation
    # for gov.processo workflows. Suggested pattern:
    # add a Many2one 'processo_id' -> 'gov.processo' (optional)
    # on knowledge.article to link procedures to processes.
    # No hard dependency on gov_processos required -
    # use try/except field declaration or check module
    # installation at runtime.
    # -------------------------------------------------------------------------

    @api.depends("parent_id", "parent_id.root_article_id")
    def _compute_root_article_id(self):
        for article in self:
            if not article.parent_id:
                article.root_article_id = article
            else:
                article.root_article_id = article.parent_id.root_article_id or article.parent_id

    @api.depends("member_ids.permission", "member_ids.partner_id", "category", "owner_partner_id", "is_locked")
    def _compute_user_flags(self):
        user = self.env.user
        is_manager = user.has_group("knowledge.group_knowledge_manager")
        partner = user.partner_id
        for article in self:
            if is_manager:
                article.user_has_access = True
                article.user_can_write = True
                continue

            membership = article.member_ids.filtered(lambda m: m.partner_id == partner)
            is_owner = article.owner_partner_id == partner
            if article.category == "workspace":
                has_access = True
            else:
                has_access = bool(is_owner or membership)
            can_write = bool(
                is_owner
                or membership.filtered(lambda m: m.permission == "write")
            )
            if article.is_locked and not is_manager:
                can_write = False
            article.user_has_access = has_access
            article.user_can_write = can_write

    def _compute_is_favorited(self):
        user = self.env.user
        if not self.ids:
            for article in self:
                article.is_favorited = False
            return
        favorites = self.env["knowledge.article.favorite"].search(
            [("article_id", "in", self.ids), ("user_id", "=", user.id)]
        )
        fav_map = {favorite.article_id.id for favorite in favorites}
        for article in self:
            article.is_favorited = article.id in fav_map

    def _compute_favorite_count(self):
        grouped = self.env["knowledge.article.favorite"].read_group(
            [("article_id", "in", self.ids)],
            ["article_id"],
            ["article_id"],
        )
        count_map = {
            item["article_id"][0]: item["article_id_count"]
            for item in grouped
            if item.get("article_id")
        }
        for article in self:
            article.favorite_count = count_map.get(article.id, 0)

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(self.env._("You cannot create recursive article trees."))

    def _is_manager(self):
        return self.env.user.has_group("knowledge.group_knowledge_manager")

    def _member_domain_for_user(self):
        return [
            ("article_id", "in", self.ids),
            ("partner_id", "=", self.env.user.partner_id.id),
        ]

    def _check_user_can_write(self):
        if self._is_manager():
            return True
        self._compute_user_flags()
        denied = self.filtered(lambda article: not article.user_can_write)
        if denied:
            raise AccessError(
                self.env._("You do not have write access to one or more selected articles.")
            )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        user_id = self.env.user.id
        for vals in vals_list:
            vals.setdefault("owner_partner_id", self.env.user.partner_id.id)
            if "body" in vals:
                vals["last_edition_date"] = now
                vals["last_edition_uid"] = user_id
        articles = super().create(vals_list)
        for article in articles:
            if not article.member_ids:
                self.env["knowledge.article.member"].create(
                    {
                        "article_id": article.id,
                        "partner_id": article.owner_partner_id.id,
                        "permission": "write",
                    }
                )
        return articles

    def write(self, vals):
        protected_fields = {
            "name",
            "body",
            "parent_id",
            "category",
            "member_ids",
            "cover_image_id",
            "icon",
            "active",
            "sequence",
            "is_locked",
        }
        if protected_fields.intersection(vals):
            self._check_user_can_write()
        if "body" in vals:
            vals = dict(vals)
            vals["last_edition_date"] = fields.Datetime.now()
            vals["last_edition_uid"] = self.env.user.id
        return super().write(vals)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.setdefault("name", self.env._("%s (copy)") % self.name)
        default["favorite_ids"] = [Command.clear()]
        default["member_ids"] = [
            Command.clear(),
            Command.create(
                {
                    "partner_id": self.env.user.partner_id.id,
                    "permission": "write",
                }
            ),
        ]
        default["owner_partner_id"] = self.env.user.partner_id.id
        return super().copy(default=default)

    def action_toggle_favorite(self):
        self.ensure_one()
        favorite_model = self.env["knowledge.article.favorite"]
        favorite = favorite_model.search(
            [("article_id", "=", self.id), ("user_id", "=", self.env.user.id)],
            limit=1,
        )
        if favorite:
            favorite.unlink()
            result = False
        else:
            favorite_model.create({"article_id": self.id, "user_id": self.env.user.id})
            result = True
        self.invalidate_recordset(["favorite_ids", "is_favorited", "favorite_count"])
        return result

    def action_set_lock(self):
        if not self._is_manager():
            raise AccessError(self.env._("Only Knowledge managers can lock articles."))
        self.write({"is_locked": True})
        return True

    def action_unset_lock(self):
        if not self._is_manager():
            raise AccessError(self.env._("Only Knowledge managers can unlock articles."))
        self.write({"is_locked": False})
        return True

    def action_make_private(self):
        for article in self:
            article._check_user_can_write()
            owner_partner = article.owner_partner_id or self.env.user.partner_id
            article.write(
                {
                    "category": "private",
                    "member_ids": [
                        Command.clear(),
                        Command.create(
                            {"partner_id": owner_partner.id, "permission": "write"}
                        ),
                    ],
                }
            )
        return True

    def action_make_shared(self):
        for article in self:
            article._check_user_can_write()
            owner_partner = article.owner_partner_id or self.env.user.partner_id
            member_commands = []
            if not article.member_ids.filtered(lambda m: m.partner_id == owner_partner):
                member_commands.append(
                    Command.create(
                        {"partner_id": owner_partner.id, "permission": "write"}
                    )
                )
            values = {"category": "shared"}
            if member_commands:
                values["member_ids"] = member_commands
            article.write(values)
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Article Members"),
            "res_model": "knowledge.article.member",
            "view_mode": "list,form",
            "domain": [("article_id", "in", self.ids)],
            "context": {"default_article_id": self[:1].id if self else False},
        }

    @api.model
    def _get_first_accessible_article(self):
        return self.search([("active", "=", True)], order="sequence, id", limit=1)

    @api.model
    def action_open_home_page(self):
        article = self._get_first_accessible_article()
        action = self.env.ref("knowledge.knowledge_article_action").read()[0]
        if article:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": article.id,
                    "views": [(self.env.ref("knowledge.knowledge_article_view_form").id, "form")],
                }
            )
        return action

    def _descendant_ids(self):
        self.ensure_one()
        descendants = self.search([("id", "child_of", self.id)])
        return descendants.ids

    def get_valid_parent_options(self, search_term=None):
        self.ensure_one()
        excluded_ids = self._descendant_ids()
        domain = [("id", "not in", excluded_ids)]
        if search_term:
            domain.append(("name", "ilike", search_term))
        return self.search(domain, order="name, id")
