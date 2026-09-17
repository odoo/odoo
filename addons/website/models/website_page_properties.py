from collections import defaultdict

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsitePagePropertiesBase(models.TransientModel):
    _name = "website.page.properties.base"
    _description = "Page Properties Base"

    target_model_id = fields.Reference(
        selection="_selection_target_model_id",
        required=True,
    )
    website_id = fields.Many2one(
        comodel_name="website",
        required=True,
    )
    menu_ids = fields.One2many(
        comodel_name="website.menu",
        compute="_compute_menu_ids",
    )
    is_in_menu = fields.Boolean(
        compute="_compute_is_in_menu",
        inverse="_inverse_is_in_menu",
    )
    url = fields.Char(required=True)
    is_homepage = fields.Boolean(
        string="Homepage",
        compute="_compute_is_homepage",
        inverse="_inverse_is_homepage",
    )
    can_publish = fields.Boolean(compute="_compute_can_publish")
    is_published = fields.Boolean(
        compute="_compute_is_published",
        inverse="_inverse_is_published",
    )

    def _selection_target_model_id(self):
        return [
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
        ]

    def _get_domain_menu(self, url=None):
        self.check_singleton()
        target = self.target_model_id
        domain = [("website_id", "=", self.website_id.id)]
        url_to_check = url or self.url
        if target and target._name == "website.page" and target.id:
            domain += ["|", ("page_id", "=", target.id), ("url", "=", url_to_check)]
        else:
            domain += [("url", "=", url_to_check)]
        return domain

    @api.depends("url", "website_id")
    def _compute_menu_ids(self):
        for record in self:
            record.menu_ids = self.env["website.menu"].search(record._get_domain_menu())  # noqa: E8507 - a transient wizard over one page; the domain is the record's own

    @api.depends("menu_ids")
    def _compute_is_in_menu(self):
        for record in self:
            record.is_in_menu = bool(record.menu_ids)

    def _inverse_is_in_menu(self):
        self.check_singleton()
        target = self.target_model_id
        if self.is_in_menu:
            if not self.menu_ids:
                _debug.lifecycle(
                    "page_added_to_menu", url=self.url, website=self.website_id.id
                )
                self.env["website.menu"].create(
                    {
                        "name": target.name,
                        "url": self.url,
                        "parent_id": self.website_id.menu_id.id,
                        "website_id": self.website_id.id,
                        "page_id": target.id
                        if (target and target._name == "website.page")
                        else False,
                    }
                )
        else:
            menus = self.menu_ids or self.env["website.menu"].search(
                self._get_domain_menu()
            )
            if menus:
                _debug.lifecycle(
                    "page_removed_from_menu",
                    url=self.url,
                    website=self.website_id.id,
                    menus=len(menus),
                )
                menus.unlink()

    @api.depends("url", "website_id.homepage_url")
    def _compute_is_homepage(self):
        for record in self:
            url = record.url
            current_homepage_url = record.website_id.homepage_url or "/"
            record.is_homepage = url in (current_homepage_url, "/")

    def _inverse_is_homepage(self):
        self.check_singleton()
        url = self.url
        if self.is_homepage:
            if url and url != "/":
                _debug.lifecycle(
                    "homepage_url_set", website=self.website_id.id, url=url
                )
                self.website_id.homepage_url = url
        elif self.website_id.homepage_url == url:
            _debug.lifecycle(
                "homepage_url_cleared", website=self.website_id.id, url=url
            )
            self.website_id.homepage_url = False

    @api.depends("target_model_id")
    def _compute_can_publish(self):
        for record in self:
            target = record.target_model_id
            if target._name == "ir.ui.view":
                record.can_publish = self._is_ir_ui_view_published(
                    target
                ) or self._is_ir_ui_view_unpublished(target)
            elif "can_publish" in target._fields:
                record.can_publish = target.can_publish
            else:
                record.can_publish = False

    @api.depends("target_model_id")
    def _compute_is_published(self):
        for record in self:
            target = record.target_model_id
            if target._name == "ir.ui.view":
                record.is_published = self._is_ir_ui_view_published(target)
            elif "is_published" in target._fields:
                record.is_published = target.is_published
            else:
                record.is_published = False

    def _inverse_is_published(self):
        self.check_singleton()
        target = self.target_model_id
        if target._name == "ir.ui.view":
            if self.can_publish:
                if self.is_published:
                    target.visibility = ""
                    target.group_ids -= self._get_ir_ui_view_unpublish_group()
                else:
                    target.visibility = "restricted_group"
                    target.group_ids += self._get_ir_ui_view_unpublish_group()
                _debug.lifecycle(
                    "view_publication",
                    view=target.id,
                    published=self.is_published,
                )
                self.env.registry.clear_cache("templates")
        elif "is_published" in target._fields:
            _debug.lifecycle(
                "record_publication",
                model=target._name,
                record=target.id,
                published=self.is_published,
            )
            target.is_published = self.is_published

    def _get_ir_ui_view_unpublish_group(self):
        return self.env.ref("base.group_user")

    def _is_ir_ui_view_unpublished(self, view):
        view.check_singleton()
        return (
            view.visibility == "restricted_group"
            and self._get_ir_ui_view_unpublish_group() in view.group_ids.all_implied_ids
        )

    def _is_ir_ui_view_published(self, view):
        view.check_singleton()
        return not view.visibility


class WebsitePageProperties(models.TransientModel):
    _name = "website.page.properties"
    _description = "Page Properties"
    _inherit = [
        "website.page.properties.base",
    ]

    target_model_id = fields.Many2one(comodel_name="website.page")
    name = fields.Char(
        related="target_model_id.name",
        readonly=False,
    )
    url = fields.Char(
        related="target_model_id.url",
        readonly=False,
    )
    date_publish = fields.Datetime(
        related="target_model_id.date_publish",
        readonly=False,
    )
    website_indexed = fields.Boolean(
        related="target_model_id.website_indexed",
        readonly=False,
    )
    visibility = fields.Selection(
        related="target_model_id.visibility",
        readonly=False,
    )
    visibility_password_display = fields.Char(
        related="target_model_id.visibility_password_display",
        readonly=False,
    )
    group_ids = fields.Many2many(
        related="target_model_id.group_ids",
        readonly=False,
    )
    is_new_page_template = fields.Boolean(
        related="target_model_id.is_new_page_template",
        readonly=False,
    )

    old_url = fields.Char()
    redirect_old_url = fields.Boolean(
        default=False,
        store=False,
    )
    redirect_type = fields.Selection(
        selection=[
            ("301", "301 Moved permanently"),
            ("302", "302 Moved temporarily"),
        ],
        default="301",
        store=False,
        required=True,
    )

    @api.depends("url", "website_id.homepage_url")
    def _compute_is_homepage(self):
        for record in self:
            url = record.url
            current_homepage_url = record.website_id.homepage_url or "/"
            record.is_homepage = url == current_homepage_url

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.old_url = record.url
        return records

    def write(self, vals):
        write_result = super().write(vals)

        if "url" not in vals:
            return write_result
        moved = [record for record in self if record.old_url != record.url]
        if not moved:
            return write_result

        # One search and one create for the whole batch. Both used to run per
        # record inside the loop, so renaming N pages cost N searches plus N
        # inserts -- and `website.rewrite` is exactly the table a bulk rename
        # touches most.
        #
        # `dfd50c87d614` fixed the search half of this independently and landed
        # in the same branch; this batches the archives and the creates as
        # well. Only the search half is gated -- `lint_n_plus_one_query` reads
        # six query methods and no write, so the inserts here were invisible to
        # it; `_checker_batch`'s module docstring says why, and this method is
        # the example it cites.
        #
        # The search carries both clauses. An earlier version of this dropped
        # the `website_id` one and filtered on the key afterwards, to avoid
        # putting a `False` into an `in` list; `dfd50c87d614` shipped exactly
        # that and it resolves to IS NULL as it should, so the reason for the
        # wider fetch was never a real one.
        Rewrite = self.env["website.rewrite"]
        website_by_record = {
            record: (vals.get("website_id") or record.website_id.id or False)
            for record in moved
        }
        obsolete_by_key = defaultdict(Rewrite.browse)
        for rewrite in Rewrite.search(
            [
                ("url_from", "in", list({record.url for record in moved})),
                ("website_id", "in", list(set(website_by_record.values()))),
            ]
        ):
            obsolete_by_key[(rewrite.url_from, rewrite.website_id.id or False)] |= (
                rewrite
            )

        to_archive = Rewrite.browse()
        redirects_to_create = []
        for record in moved:
            website_id = website_by_record[record]
            _debug.lifecycle(
                "page_properties_url_changed",
                page=record.target_model_id.id,
                old=record.old_url,
                new=record.url,
                redirect=bool(vals.get("redirect_old_url")),
            )
            if obsolete := obsolete_by_key.get((record.url, website_id)):
                _debug.lifecycle(
                    "obsolete_rewrites_archived",
                    page=record.target_model_id.id,
                    url=record.url,
                    rewrites=obsolete.ids,
                )
                to_archive |= obsolete
            if vals.get("redirect_old_url"):
                redirects_to_create.append(
                    {
                        "name": vals.get("name") or record.name,
                        "redirect_type": vals.get("redirect_type")
                        or record.redirect_type,
                        "url_from": record.old_url,
                        "url_to": record.url,
                        "website_id": website_id,
                    }
                )

        if to_archive:
            to_archive.active = False
        if redirects_to_create:
            Rewrite.create(redirects_to_create)
        for record in moved:
            record.old_url = record.url

        return write_result
