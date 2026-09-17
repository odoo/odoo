import logging
import uuid

import werkzeug

from odoo import api, fields, models
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrUiView(models.Model):
    _name = "ir.ui.view"

    _inherit = ["ir.ui.view", "mixin.website.seo.metadata"]

    website_id = fields.Many2one(
        comodel_name="website",
        ondelete="cascade",
    )
    page_ids = fields.One2many(
        comodel_name="website.page",
        inverse_name="view_id",
    )
    controller_page_ids = fields.One2many(
        comodel_name="website.controller.page",
        inverse_name="view_id",
    )
    first_page_id = fields.Many2one(
        comodel_name="website.page",
        string="Website Page",
        compute="_compute_first_page_id",
        help="First page linked to this view",
    )
    track = fields.Boolean(
        default=False,
        help="Allow to specify for one page of the website to be trackable or not",
    )
    visibility = fields.Selection(
        selection=[
            ("", "Public"),
            ("connected", "Signed In"),
            ("restricted_group", "Restricted Group"),
            ("password", "With Password"),
        ],
        default="",
    )
    visibility_password = fields.Char(
        copy=False,
        groups="base.group_system",
    )
    visibility_password_display = fields.Char(
        compute="_compute_visibility_password_display",
        inverse="_inverse_visibility_password_display",
        groups="website.group_website_designer",
    )

    @api.depends("visibility_password")
    def _compute_visibility_password_display(self):
        for r in self:
            r.visibility_password_display = (
                r.sudo().visibility_password and "********"
            ) or ""

    def _inverse_visibility_password_display(self):
        crypt_context = self.env.user._get_crypt_context()
        for r in self:
            if r.type == "qweb":
                r.check_access("write")
                _debug.lifecycle(
                    "visibility_password_set",
                    view=r.id,
                    cleared=not r.visibility_password_display,
                )
                r.sudo().visibility_password = (
                    r.visibility_password_display
                    and crypt_context.hash(r.visibility_password_display)
                ) or ""

    def _compute_first_page_id(self):
        pages = self.env["website.page"].search([("view_id", "in", self.ids)])
        first_by_view = {}
        for page in pages:
            first_by_view.setdefault(page.view_id.id, page)
        for view in self:
            view.first_page_id = first_by_view.get(view.id, False)

    @api.model_create_multi
    def create(self, vals_list):
        website_id = self.env.context.get("website_id", False)
        if not website_id:
            return super().create(vals_list)

        for vals in vals_list:
            if "website_id" not in vals:
                vals["website_id"] = website_id
            else:
                new_website_id = vals["website_id"]
                if not new_website_id:
                    _debug.logic(
                        "view_create_refused",
                        reason="generic_from_website_env",
                        website=website_id,
                    )
                    raise ValueError(
                        f"Trying to create a generic view from a website {website_id} environment"
                    )
                if new_website_id != website_id:
                    _debug.logic(
                        "view_create_refused",
                        reason="website_mismatch",
                        website=website_id,
                        requested=new_website_id,
                    )
                    raise ValueError(
                        f"Trying to create a view for website {new_website_id} from a website {website_id} environment"
                    )
        return super().create(vals_list)

    @api.depends("website_id", "key")
    @api.depends_context("display_key", "display_website")
    def _compute_display_name(self):
        if not (
            self.env.context.get("display_key")
            or self.env.context.get("display_website")
        ):
            return super()._compute_display_name()

        for view in self:
            view_name = view.name
            if self.env.context.get("display_key"):
                view_name += " <%s>" % view.key
            if self.env.context.get("display_website") and view.website_id:
                view_name += " [%s]" % view.website_id.name
            view.display_name = view_name
        return None

    def write(self, vals):
        current_website_id = self.env.context.get("website_id")
        if not current_website_id or self.env.context.get("no_cow"):
            return super().write(vals)

        for view in self.with_context(active_test=False).sorted("website_id.id"):
            if not view.key and not vals.get("key"):
                view.with_context(no_cow=True).key = (
                    "website.key_%s" % str(uuid.uuid4())[:6]
                )

            pages = view.page_ids

            if view.website_id:
                _debug.logic(
                    "cow_write", by="already_specific", view=view.id, key=view.key
                )
                super(IrUiView, view).write(vals)
                continue

            pages.flush_recordset()
            pages.invalidate_recordset()

            website_specific_view = view.search(
                [("key", "=", view.key), ("website_id", "=", current_website_id)],
                limit=1,
            )
            if website_specific_view:
                _debug.logic(
                    "cow_write",
                    by="existing_specific",
                    view=view.id,
                    specific=website_specific_view.id,
                )
                super(IrUiView, website_specific_view).write(vals)
                continue

            copy_vals = {"website_id": current_website_id, "key": view.key}
            if vals.get("inherit_id"):
                copy_vals["inherit_id"] = vals["inherit_id"]
                if "mode" in vals:
                    copy_vals["mode"] = vals["mode"]
                # the copy carries the generic's mode; the change implies
                # the same default it would on the generic itself
                copy_vals = view._default_mode(copy_vals)
            website_specific_view = view.copy(copy_vals)

            website = view.env["website"].browse(current_website_id)
            _debug.lifecycle(
                "cow_copied",
                view=view.id,
                key=view.key,
                specific=website_specific_view.id,
                website=current_website_id,
            )
            view._create_website_specific_pages_for_view(website_specific_view, website)

            for (
                inherit_child
            ) in view.inherit_children_ids._filtered_most_specific().sorted(
                key=lambda v: (v.priority, v.id)
            ):
                if inherit_child.website_id.id == current_website_id:
                    child = inherit_child.copy(
                        {
                            "inherit_id": website_specific_view.id,
                            "key": inherit_child.key,
                        }
                    )
                    inherit_child._create_website_specific_pages_for_view(
                        child, website
                    )
                    inherit_child.inherit_children_ids.write({"inherit_id": child.id})
                    _debug.lifecycle(
                        "cow_child_rehomed",
                        child=inherit_child.id,
                        copy=child.id,
                        parent=website_specific_view.id,
                    )
                    inherit_child.unlink()
                else:
                    _debug.lifecycle(
                        "cow_child_reparented",
                        child=inherit_child.id,
                        parent=website_specific_view.id,
                    )
                    inherit_child.write({"inherit_id": website_specific_view.id})

            super(IrUiView, website_specific_view).write(vals)

        return True

    def _load_records_write_on_cow(self, cow_view, inherit_id, values):
        inherit_id = self.search(
            [
                ("key", "=", self.browse(inherit_id).key),
                ("website_id", "in", (False, cow_view.website_id.id)),
            ],
            order="website_id",
            limit=1,
        ).id
        values["inherit_id"] = inherit_id
        cow_view.with_context(no_cow=True).write(values)

    def _create_all_specific_views(self, processed_modules):
        regex = "^(%s)[.]" % "|".join(processed_modules)
        query = """
            SELECT generic.id, ARRAY[array_agg(spec_parent.id), array_agg(spec_parent.website_id)]
              FROM ir_ui_view generic
        INNER JOIN ir_ui_view generic_parent ON generic_parent.id = generic.inherit_id
        INNER JOIN ir_ui_view spec_parent ON spec_parent.key = generic_parent.key
         LEFT JOIN ir_ui_view specific ON specific.key = generic.key AND specific.website_id = spec_parent.website_id
             WHERE generic.type='qweb'
               AND generic.website_id IS NULL
               AND generic.key ~ %s
               AND spec_parent.website_id IS NOT NULL
               AND specific.id IS NULL
          GROUP BY generic.id
        """
        self.env.cr.execute(query, (regex,))
        result = dict(self.env.cr.fetchall())
        _debug.pipeline(
            "specific_views_to_create",
            modules=len(processed_modules),
            generic_views=len(result),
        )

        for record in self.browse(result.keys()):
            specific_parent_view_ids, website_ids = result[record.id]
            for specific_parent_view_id, website_id in zip(
                specific_parent_view_ids, website_ids, strict=False
            ):
                record.with_context(website_id=website_id).write(
                    {
                        "inherit_id": specific_parent_view_id,
                    }
                )
        super()._create_all_specific_views(processed_modules)

    def unlink(self):
        if not self:
            return True
        current_website_id = self.env.context.get("website_id")

        preserved_view_ids = set()
        if current_website_id and not self.env.context.get("no_cow"):
            generic_views = self.filtered(lambda view: not view.website_id)
            other_websites = self.env["website"].search(
                [("id", "!=", current_website_id)]
            )
            for view in generic_views:
                for w in other_websites:
                    view.with_context(website_id=w.id).write({"name": view.name})
            if generic_views and other_websites:
                first_per_website_key = {}
                for preserved in self.search(
                    [
                        ("key", "in", generic_views.mapped("key")),
                        ("website_id", "in", other_websites.ids),
                    ]
                ):
                    first_per_website_key.setdefault(
                        (preserved.key, preserved.website_id.id), preserved.id
                    )
                preserved_view_ids = set(first_per_website_key.values())

        specific_views = self.env["ir.ui.view"]
        if self and not self.pool.ready:
            for view in self.filtered(lambda view: not view.website_id):
                specific_views += view._get_views_specific()
            specific_views -= self.browse(preserved_view_ids)

        _debug.lifecycle(
            "unlink",
            views=self,
            count=len(self),
            specific=len(specific_views),
            preserved=len(preserved_view_ids),
        )
        result = super(IrUiView, self + specific_views).unlink()
        self.env.registry.clear_cache("templates")
        return result

    def _create_website_specific_pages_for_view(self, new_view, website):
        for page in self.page_ids:
            new_page = page.copy(
                {
                    "view_id": new_view.id,
                    "is_published": page.is_published,
                }
            )
            page.menu_ids.filtered(
                lambda m: m.website_id.id == website.id
            ).page_id = new_page.id
            _debug.lifecycle(
                "specific_page_created",
                page=page.id,
                copy=new_page.id,
                view=new_view.id,
                website=website.id,
            )

    def get_view_hierarchy(self):
        self.check_singleton()
        top_level_view = self
        while top_level_view.inherit_id:
            top_level_view = top_level_view.inherit_id
        top_level_view = top_level_view.with_context(active_test=False)
        sibling_views = top_level_view.search_read(
            [("key", "=", top_level_view.key), ("id", "!=", top_level_view.id)]
        )
        return {
            "sibling_views": sibling_views,
            "hierarchy": top_level_view._prepare_hierarchy_datastructure(),
        }

    def _prepare_hierarchy_datastructure(self):
        inherit_children = [
            child._prepare_hierarchy_datastructure()
            for child in self.inherit_children_ids
        ]
        return {
            "id": self.id,
            "name": self.name,
            "inherit_children": inherit_children,
            "arch_updated": self.arch_updated,
            "website_name": self.website_id.name if self.website_id else False,
            "active": self.active,
            "key": self.key,
        }

    @api.model
    def get_related_views(self, key, bundles=False):
        current_website = self.env["website"].get_current_website()
        return (
            super(IrUiView, self.with_context(website_id=current_website.id))
            .get_related_views(key, bundles=bundles)
            .with_context(
                lang=current_website.default_lang_id.code,
            )
        )

    def _filtered_most_specific(self):
        current_website_id = self.env.context.get("website_id")
        if not current_website_id:
            return self.filtered(lambda view: not view.website_id)

        specific_views_keys = {
            view.key
            for view in self
            if view.website_id.id == current_website_id and view.key
        }
        most_specific_views = [
            view
            for view in self
            if (view.website_id and view.website_id.id == current_website_id)
            or (not view.website_id and view.key not in specific_views_keys)
        ]

        _debug.perf.count(
            "most_specific_filtered",
            website=current_website_id,
            candidates=len(self),
            kept=len(most_specific_views),
        )
        return self.browse().union(*most_specific_views)

    @api.model
    def _view_get_inherited_children(self, view):
        extensions = super()._view_get_inherited_children(view)
        return extensions._filtered_most_specific()

    @api.model
    def _get_domain_inheriting_views(self):
        domain = super()._get_domain_inheriting_views()
        current_website = self.env["website"].browse(self.env.context.get("website_id"))
        website_views_domain = current_website.website_domain()
        if current_website:
            domain = domain.map_conditions(
                lambda cond: cond if cond.field_expr != "active" else Domain.TRUE
            )
        return website_views_domain & domain

    @api.model
    def _get_views_inheriting(self):
        views = self
        if not views.env.context.get("website_id"):
            # a website-specific view resolves in its own website: outside
            # one, the generic domain would drop it from its own tree. The
            # generic resolution comes first -- its fetch is the one that
            # reads the chain -- and only a specific chain resolves again
            generic = super()._get_views_inheriting()
            website_ids = views.website_id.ids
            if len(website_ids) != 1:
                return generic
            _debug.logic(
                "views_inheriting.website_from_views",
                views=len(views),
                website=website_ids[0],
            )
            views = views.with_context(website_id=website_ids[0])

        views = super(
            IrUiView, views.with_context(active_test=False)
        )._get_views_inheriting()
        return views._filtered_most_specific().filtered("active")

    def _get_sql_view_loaded(self, view, modules):
        loaded = super()._get_sql_view_loaded(view, modules)
        if not self.env.context.get("website_id"):
            return loaded
        _debug.logic(
            "loaded_views_include_website_copies",
            website=self.env.context.get("website_id"),
        )
        generic = SQL.identifier("generic")
        return SQL(
            """(%s OR (%s.website_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM ir_ui_view generic
                WHERE generic.key = %s.key
                AND generic.website_id IS NULL
                AND %s
            )))""",
            loaded,
            view,
            view,
            super()._get_sql_view_loaded(generic, modules),
        )

    @api.model
    def _get_field_names_in_cached_template(self):
        return super()._get_field_names_in_cached_template() + [
            "active",
            "visibility",
            "track",
        ]

    @api.model
    def _get_template_cache_keys_minimal(self):
        return super()._get_template_cache_keys_minimal() + (
            self.env.context.get("website_id"),
        )

    @api.model
    def _get_domain_template(self, xmlids):
        domain = super()._get_domain_template(xmlids)
        return domain & Domain(
            "website_id", "in", (False, self.env.context.get("website_id", False))
        )

    @api.model
    def _get_views_by_ref(self, ids_or_xmlids):
        data = super()._get_views_by_ref(ids_or_xmlids)
        for key in list(data):
            if isinstance(data[key], MissingError):
                _debug.logic(
                    "view_ref_missing",
                    ref=key,
                    website=self.env.context.get("website_id"),
                )
                data[key] = MissingError(
                    self.env._(
                        "%(error)s (website: %(website_id)s)",
                        error=data[key],
                        website_id=self.env.context.get("website_id"),
                    )
                )
        return data

    @api.model
    def _get_template_order(self):
        return f"website_id asc, {super()._get_template_order()}"

    def _get_cached_visibility(self):
        info = self._get_cached_template_info(self.id, _view=self)
        if info["error"]:
            raise info["error"]
        return info["visibility"]

    def _handle_visibility(self, do_raise=True):
        error = False

        self = self.sudo()

        visibility = self._get_cached_visibility()

        if visibility:
            request.future_response.headers["Cache-Control"] = (
                "private, no-store, max-age=0"
            )

        if visibility and not request.env.user.has_group(
            "website.group_website_designer"
        ):
            if visibility == "connected" and request.website.is_public_user():
                _debug.logic("visibility_refused", reason="connected", view=self.id)
                error = werkzeug.exceptions.Forbidden()
            elif visibility == "password" and self.id not in request.session.get(
                "views_unlock", []
            ):
                pwd = request.params.get("visibility_password")
                stored_password = self.visibility_password
                if (
                    pwd
                    and stored_password
                    and self.env.user._get_crypt_context().is_password_valid(
                        pwd, stored_password
                    )
                ):
                    _debug.lifecycle("visibility_unlocked", view=self.id)
                    request.session["views_unlock"] = [
                        *request.session.get("views_unlock", []),
                        self.id,
                    ]
                else:
                    _debug.logic(
                        "visibility_refused",
                        reason="password",
                        view=self.id,
                        supplied=bool(pwd),
                    )
                    error = werkzeug.exceptions.Forbidden(
                        "website_visibility_password_required"
                    )

            if visibility not in ("password", "connected"):
                try:
                    self._check_view_access()
                except AccessError:
                    _debug.logic(
                        "visibility_refused",
                        reason="view_access",
                        view=self.id,
                        visibility=visibility,
                    )
                    error = werkzeug.exceptions.Forbidden()

        if error:
            if do_raise:
                raise error
            return False
        return True

    @api.readonly
    @api.model
    def render_public_asset(self, template, values=None):
        if request and hasattr(request, "website"):
            return super(
                IrUiView, self.with_context(website_id=request.website.id)
            ).render_public_asset(template, values=values)
        return super().render_public_asset(template, values=values)

    def _render_template(self, template, values=None):
        view = self._get_template_view(template).sudo()
        view._handle_visibility(do_raise=True)
        if values is None:
            values = {}
        if "main_object" not in values:
            values["main_object"] = view
        return super()._render_template(template, values=values)

    @api.model
    def get_default_lang_code(self):
        website_id = self.env.context.get("website_id")
        if website_id:
            return self.env["website"].browse(website_id).default_lang_id.code
        else:
            return super().get_default_lang_code()

    @api.model
    def _save_oe_structure_hook(self):
        res = super()._save_oe_structure_hook()
        res["website_id"] = self.env["website"].get_current_website().id
        return res

    @api.model
    def _set_noupdate(self):
        if not self.env.context.get("website_id"):
            super()._set_noupdate()

    def save(self, value, xpath=None):
        self.check_singleton()
        current_website = self.env["website"].get_current_website()
        if xpath and self.key and current_website:
            website_specific_view = self.env["ir.ui.view"].search(
                [("key", "=", self.key), ("website_id", "=", current_website.id)],
                limit=1,
            )
            if website_specific_view:
                _debug.logic(
                    "save_retargeted",
                    view=self.id,
                    specific=website_specific_view.id,
                    website=current_website.id,
                )
                self = website_specific_view
        _debug.lifecycle("save", view=self.id, key=self.key, xpath=xpath or None)
        super().save(value, xpath=xpath)

    @api.model
    def _get_allowed_root_attrs(self):
        return (
            super()._get_allowed_root_attrs()
            + [
                "data-bg-video-src",
                "data-shape",
                "data-scroll-background-ratio",
                "data-visibility",
                "data-visibility-id",
                "data-visibility-selectors",
            ]
            + [
                "data-visibility-value-" + param + suffix
                for param in (
                    "country",
                    "lang",
                    "logged",
                    "utm-campaign",
                    "utm-medium",
                    "utm-source",
                )
                for suffix in ("", "-rule")
            ]
        )

    @api.model
    def _snippet_save_view_values_hook(self):
        res = super()._snippet_save_view_values_hook()
        website_id = self.env.context.get("website_id")
        if website_id:
            res["website_id"] = website_id
        return res

    def _update_field_translations(
        self, field_name, translations, digest=None, source_lang=""
    ):
        return super(
            IrUiView, self.with_context(no_cow=True)
        )._update_field_translations(
            field_name, translations, digest=digest, source_lang=source_lang
        )

    def _get_base_lang(self):
        self.check_singleton()
        website = self.website_id
        if website:
            return website.default_lang_id.code
        return super()._get_base_lang()
