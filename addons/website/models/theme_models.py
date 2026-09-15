import logging

from odoo import api, fields, models, modules
from odoo.libs.debug_log import DebugLog
from odoo.modules.module import get_resource_from_path
from odoo.tools.translate import xml_translate

from odoo.addons.base.models.ir_asset import (
    AFTER_DIRECTIVE,
    APPEND_DIRECTIVE,
    BEFORE_DIRECTIVE,
    DEFAULT_SEQUENCE,
    INCLUDE_DIRECTIVE,
    PREPEND_DIRECTIVE,
    REMOVE_DIRECTIVE,
    REPLACE_DIRECTIVE,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ThemeIrAsset(models.Model):
    _name = "theme.ir.asset"
    _description = "Theme Asset"

    key = fields.Char()
    name = fields.Char(required=True)
    bundle = fields.Char(required=True)
    directive = fields.Selection(
        selection=[
            (APPEND_DIRECTIVE, "Append"),
            (PREPEND_DIRECTIVE, "Prepend"),
            (AFTER_DIRECTIVE, "After"),
            (BEFORE_DIRECTIVE, "Before"),
            (REMOVE_DIRECTIVE, "Remove"),
            (REPLACE_DIRECTIVE, "Replace"),
            (INCLUDE_DIRECTIVE, "Include"),
        ],
        default=APPEND_DIRECTIVE,
    )
    path = fields.Char(required=True)
    target = fields.Char()
    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=DEFAULT_SEQUENCE,
        required=True,
    )
    copy_ids = fields.One2many(
        comodel_name="ir.asset",
        inverse_name="theme_template_id",
        string="Assets using a copy of me",
        copy=False,
        readonly=True,
    )

    def _convert_to_base_model(self, website, **kwargs):
        self.check_singleton()
        return {
            "name": self.name,
            "key": self.key,
            "bundle": self.bundle,
            "directive": self.directive,
            "path": self.path,
            "target": self.target,
            "active": self.active,
            "sequence": self.sequence,
            "website_id": website.id,
            "theme_template_id": self.id,
        }


class ThemeIrUiView(models.Model):
    _name = "theme.ir.ui.view"
    _description = "Theme UI View"

    def _default_arch_fs(self):
        if "install_filename" not in self.env.context:
            return ""
        path_info = get_resource_from_path(self.env.context["install_filename"])
        if path_info:
            return path_info.addons_path
        return None

    name = fields.Char(required=True)
    key = fields.Char()
    type = fields.Char()
    priority = fields.Integer(
        default=DEFAULT_SEQUENCE,
        required=True,
    )
    mode = fields.Selection(
        selection=[("primary", "Base view"), ("extension", "Extension View")]
    )
    active = fields.Boolean(default=True)
    arch = fields.Text(translate=xml_translate)
    arch_fs = fields.Char(default=_default_arch_fs)
    inherit_id = fields.Reference(
        selection=[
            ("ir.ui.view", "ir.ui.view"),
            ("theme.ir.ui.view", "theme.ir.ui.view"),
        ]
    )
    copy_ids = fields.One2many(
        comodel_name="ir.ui.view",
        inverse_name="theme_template_id",
        string="Views using a copy of me",
        copy=False,
        readonly=True,
    )
    customize_show = fields.Boolean()

    def _convert_to_base_model(self, website, **kwargs):
        self.check_singleton()
        inherit = self.inherit_id
        if self.inherit_id and self.inherit_id._name == "theme.ir.ui.view":
            inherit = self.inherit_id.with_context(active_test=False).copy_ids.filtered(
                lambda x: x.website_id == website
            )
            if not inherit:
                _debug.logic(
                    "theme_view_deferred",
                    reason="parent_not_copied_yet",
                    view=self.id,
                    key=self.key,
                )
                return False

        if inherit and inherit.website_id != website:
            website_specific_inherit = (
                self.env["ir.ui.view"]
                .with_context(active_test=False)
                .search(
                    [("key", "=", inherit.key), ("website_id", "=", website.id)],
                    limit=1,
                )
            )
            if website_specific_inherit:
                _debug.logic(
                    "theme_view_inherit_retargeted",
                    view=self.id,
                    inherit=website_specific_inherit.id,
                    website=website.id,
                )
                inherit = website_specific_inherit

        new_view = {
            "type": self.type or "qweb",
            "name": self.name,
            "arch": self.arch,
            "key": self.key,
            "inherit_id": inherit and inherit.id,
            "arch_fs": self.arch_fs,
            "priority": self.priority,
            "active": self.active,
            "theme_template_id": self.id,
            "website_id": website.id,
            "customize_show": self.customize_show,
        }

        if self.mode:
            new_view["mode"] = self.mode

        return new_view


class ThemeIrAttachment(models.Model):
    _name = "theme.ir.attachment"
    _description = "Theme Attachments"

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    url = fields.Char()
    copy_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="theme_template_id",
        string="Attachment using a copy of me",
        copy=False,
        readonly=True,
    )

    def _convert_to_base_model(self, website, **kwargs):
        self.check_singleton()
        return {
            "key": self.key,
            "public": True,
            "res_model": "ir.ui.view",
            "type": "url",
            "name": self.name,
            "url": self.url,
            "website_id": website.id,
            "theme_template_id": self.id,
        }


class ThemeWebsiteMenu(models.Model):
    _name = "theme.website.menu"
    _description = "Website Theme Menu"

    name = fields.Char(
        translate=True,
        required=True,
    )
    url = fields.Char(default="")
    page_id = fields.Many2one(
        comodel_name="theme.website.page",
        index="btree_not_null",
        ondelete="cascade",
    )
    new_window = fields.Boolean()
    sequence = fields.Integer()
    parent_id = fields.Many2one(
        comodel_name="theme.website.menu",
        index=True,
        ondelete="cascade",
    )
    mega_menu_content = fields.Html()
    mega_menu_classes = fields.Char()

    use_main_menu_as_parent = fields.Boolean(default=True)
    copy_ids = fields.One2many(
        comodel_name="website.menu",
        inverse_name="theme_template_id",
        string="Menu using a copy of me",
        copy=False,
        readonly=True,
    )

    def _convert_to_base_model(self, website, **kwargs):
        self.check_singleton()
        page_id = self.page_id.copy_ids.filtered(lambda x: x.website_id == website)

        parent_id = False
        if self.parent_id:
            parent_id = self.parent_id.copy_ids.filtered(
                lambda x: x.website_id == website
            )
        elif self.use_main_menu_as_parent:
            parent_id = website.menu_id

        return {
            "name": self.name,
            "url": self.url,
            "page_id": (page_id and page_id.id) or False,
            "new_window": self.new_window,
            "sequence": self.sequence,
            "parent_id": (parent_id and parent_id.id) or False,
            "website_id": website.id,
            "mega_menu_content": self.mega_menu_content,
            "mega_menu_classes": self.mega_menu_classes,
            "theme_template_id": self.id,
        }


class ThemeWebsitePage(models.Model):
    _name = "theme.website.page"
    _description = "Website Theme Page"
    _inherit = [
        "mixin.website.page_options",
    ]

    url = fields.Char()
    view_id = fields.Many2one(
        comodel_name="theme.ir.ui.view",
        index=True,
        required=True,
        ondelete="cascade",
    )
    website_indexed = fields.Boolean(
        string="Page Indexed",
        default=True,
    )
    is_published = fields.Boolean()
    is_new_page_template = fields.Boolean(string="New Page Template")

    copy_ids = fields.One2many(
        comodel_name="website.page",
        inverse_name="theme_template_id",
        string="Page using a copy of me",
        copy=False,
        readonly=True,
    )

    def _convert_to_base_model(self, website, **kwargs):
        self.check_singleton()
        view_id = self.view_id.copy_ids.filtered(lambda x: x.website_id == website)
        if not view_id:
            _debug.logic(
                "theme_page_deferred",
                reason="view_not_copied_yet",
                page=self.id,
                url=self.url,
            )
            return False

        return {
            "url": self.url,
            "view_id": view_id.id,
            "website_indexed": self.website_indexed,
            "is_published": self.is_published,
            "is_new_page_template": self.is_new_page_template,
            "header_overlay": self.header_overlay,
            "header_color": self.header_color,
            "header_text_color": self.header_text_color,
            "header_visible": self.header_visible,
            "footer_visible": self.footer_visible,
            "theme_template_id": self.id,
        }


class ThemeUtils(models.AbstractModel):
    _name = "theme.utils"
    _description = "Theme Utils"
    _auto = False

    _header_templates = [
        "website.template_header_hamburger",
        "website.template_header_vertical",
        "website.template_header_sidebar",
        "website.template_header_boxed",
        "website.template_header_stretch",
        "website.template_header_search",
        "website.template_header_sales_one",
        "website.template_header_sales_two",
        "website.template_header_sales_three",
        "website.template_header_sales_four",
        "website.template_header_default",
    ]
    _footer_templates = [
        "website.template_footer_descriptive",
        "website.template_footer_centered",
        "website.template_footer_links",
        "website.template_footer_minimalist",
        "website.template_footer_contact",
        "website.template_footer_call_to_action",
        "website.template_footer_headline",
        "website.template_footer_mega",
        "website.template_footer_mega_columns",
        "website.template_footer_mega_links",
        "website.template_footer_mega_cards",
        "website.footer_custom",
    ]

    def _post_copy(self, mod):
        theme_post_copy = "_%s_post_copy" % mod.name
        if hasattr(self, theme_post_copy):
            _logger.info("Executing method %s", theme_post_copy)
            _debug.pipeline("theme_post_copy", theme=mod.name, method=theme_post_copy)
            method = getattr(self, theme_post_copy)
            return method(mod)
        _debug.logic("theme_post_copy_absent", theme=mod.name)
        return False

    @api.model
    def _reset_default_config(self):
        _debug.lifecycle(
            "theme_config_reset",
            website=self.env["website"].get_current_website().id,
        )
        self.env["website.assets"].update_scss_customization(
            "/website/static/src/scss/options/user_values.scss",
            {
                "font": "null",
                "headings-font": "null",
                "navbar-font": "null",
                "buttons-font": "null",
                "color-palettes-number": "null",
                "color-palettes-name": "null",
                "btn-ripple": "null",
                "header-template": "null",
                "footer-template": "null",
                "footer-scrolltop": "null",
            },
        )

        self.disable_asset("website.ripple_effect_scss")
        self.disable_asset("website.ripple_effect_js")

        for view in self._header_templates[:-1]:
            self.disable_view(view)
        self.enable_view(self._header_templates[-1])

        for view in self._footer_templates[:-1]:
            self.disable_view(view)
        self.enable_view(self._footer_templates[-1])

        self.disable_view("website.option_footer_scrolltop")

    @api.model
    def _toggle_asset(self, key, active):
        ThemeIrAsset = self.env["theme.ir.asset"].sudo().with_context(active_test=False)
        obj = ThemeIrAsset.search([("key", "=", key)])
        website = self.env["website"].get_current_website()
        if obj:
            obj = obj.copy_ids.filtered(lambda x: x.website_id == website)
        else:
            Asset = self.env["ir.asset"].sudo().with_context(active_test=False)
            obj = Asset.search([("key", "=", key)], limit=1)
            has_specific = (
                obj.key
                and Asset.search_count(
                    [("key", "=", obj.key), ("website_id", "=", website.id)]
                )
                >= 1
            )
            if not has_specific and active == obj.active:
                _debug.logic(
                    "asset_toggle_noop", key=key, active=active, website=website.id
                )
                return
        _debug.lifecycle(
            "asset_toggled",
            key=key,
            active=active,
            website=website.id,
            assets=obj,
        )
        obj.write({"active": active})

    @api.model
    def _toggle_view(self, xml_id, active):
        obj = self.env.ref(xml_id)
        website = self.env["website"].get_current_website()
        if obj._name == "theme.ir.ui.view":
            obj = obj.with_context(active_test=False)
            obj = obj.copy_ids.filtered(lambda x: x.website_id == website)
        else:
            View = self.env["ir.ui.view"].with_context(active_test=False)
            has_specific = (
                obj.key
                and View.search_count(
                    [("key", "=", obj.key), ("website_id", "=", website.id)]
                )
                >= 1
            )
            if not has_specific and active == obj.active:
                _debug.logic(
                    "view_toggle_noop",
                    xmlid=xml_id,
                    active=active,
                    website=website.id,
                )
                return
        _debug.lifecycle(
            "view_toggled",
            xmlid=xml_id,
            active=active,
            website=website.id,
            views=obj,
        )
        obj.write({"active": active})

    @api.model
    def enable_asset(self, name):
        self._toggle_asset(name, True)

    @api.model
    def disable_asset(self, name):
        self._toggle_asset(name, False)

    @api.model
    def enable_view(self, xml_id):
        if xml_id in self._header_templates:
            for view in self._header_templates:
                self.disable_view(view)
        elif xml_id in self._footer_templates:
            for view in self._footer_templates:
                self.disable_view(view)
        self._toggle_view(xml_id, True)

    @api.model
    def disable_view(self, xml_id):
        self._toggle_view(xml_id, False)


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    theme_template_id = fields.Many2one(
        comodel_name="theme.ir.ui.view",
        index="btree_not_null",
        copy=False,
    )

    def write(self, vals):
        test_mode = modules.module.current_test
        if self.pool.ready and not test_mode:
            return super().write(vals)
        no_arch_updated_views = other_views = self.env["ir.ui.view"]
        for record in self:
            arch = vals.get("arch", vals.get("arch_base"))
            if record.theme_template_id and record.theme_template_id.arch == arch:
                no_arch_updated_views += record
            else:
                other_views += record
        res = super(IrUiView, other_views).write(vals)
        if no_arch_updated_views:
            _debug.logic(
                "theme_arch_unchanged",
                views=no_arch_updated_views,
                count=len(no_arch_updated_views),
            )
            res &= super(IrUiView, no_arch_updated_views).write(
                dict(vals, arch_updated=False)
            )
        return res


class IrAsset(models.Model):
    _inherit = "ir.asset"

    theme_template_id = fields.Many2one(
        comodel_name="theme.ir.asset",
        index="btree_not_null",
        copy=False,
    )


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    key = fields.Char(copy=False)
    theme_template_id = fields.Many2one(
        comodel_name="theme.ir.attachment",
        index="btree_not_null",
        copy=False,
    )


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    theme_template_id = fields.Many2one(
        comodel_name="theme.website.menu",
        index="btree_not_null",
        copy=False,
    )


class WebsitePage(models.Model):
    _inherit = "website.page"

    theme_template_id = fields.Many2one(
        comodel_name="theme.website.page",
        index="btree_not_null",
        copy=False,
    )
