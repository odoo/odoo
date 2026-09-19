from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsiteControllerPage(models.Model):
    _name = "website.controller.page"
    _inherits = {"ir.ui.view": "view_id"}
    _inherit = [
        "mixin.website.published.multi",
        "mixin.website.searchable",
    ]
    _description = "Model Page"
    _order = "website_id, id DESC"
    _unique_name_slugified = models.UniqueIndex(
        "(name_slugified, website_id) "
        "WHERE name_slugified IS NOT NULL AND website_id IS NOT NULL",
        "url should be unique per website",
    )

    view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Listing view",
        index=True,
        required=True,
        ondelete="cascade",
    )
    record_view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Record view",
        ondelete="cascade",
    )
    menu_ids = fields.One2many(
        comodel_name="website.menu",
        inverse_name="controller_page_id",
        string="Related Menus",
    )

    website_id = fields.Many2one(  # noqa: E8529  UNIQUE (name_slugified, website_id) partial
        related="view_id.website_id",
        store=True,
        readonly=False,
        ondelete="cascade",
    )

    name = fields.Char(
        string="The name is used to generate the URL and is shown in the browser title bar",
        compute="_compute_name",
        inverse="_inverse_name",
        precompute=True,
        store=True,
        required=True,
    )
    name_slugified = fields.Char(
        string="URL",
        compute="_compute_name_slugified",
        inverse="_inverse_name_slugified",
        precompute=True,
        store=True,
        help="The name of the page usable in a URL",
    )
    url_demo = fields.Char(
        string="Demo URL",
        compute="_compute_url_demo",
    )

    record_domain = fields.Char(
        string="Domain",
        help="Domain to restrict records that can be viewed publicly",
    )
    default_layout = fields.Selection(
        selection=[
            ("grid", "Grid"),
            ("list", "List"),
        ],
        default="grid",
    )

    def _check_user_has_model_access(self):
        for model_id in self.mapped("model_id"):
            Model = self.env[model_id.model]
            if Model._transient or Model._abstract or not Model._auto:
                _debug.logic(
                    "controller_page_refused",
                    reason="not_a_concrete_model",
                    model=model_id.model,
                )
                raise ValidationError(
                    self.env._("A page must be set to display a concrete model.")
                )
            Model.check_access("read")

    @api.depends("view_id")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.view_id.name

    def _inverse_name(self):
        for rec in self:
            if rec.view_id:
                rec.view_id.name = rec.name

    @api.depends("model_id", "name")
    def _compute_name_slugified(self):
        for rec in self:
            if not rec.model_id:
                rec.name_slugified = False
                continue
            rec.name_slugified = self.env["ir.http"]._slugify(rec.name or "")

    def _inverse_name_slugified(self):
        for rec in self:
            rec.name_slugified = self.env["ir.http"]._slugify(rec.name_slugified)

    @api.depends("name_slugified")
    def _compute_url_demo(self):
        for rec in self:
            if not rec.name_slugified:
                rec.url_demo = ""
                continue
            url = ["", "model", rec.name_slugified]
            rec.url_demo = "/".join(url)

    def _default_is_published(self):
        return False

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        _debug.lifecycle("create", pages=res, count=len(res))
        res._check_user_has_model_access()
        return res

    def write(self, vals):
        res = super().write(vals)
        _debug.lifecycle("write", pages=self, count=len(self), fields=sorted(vals))
        if "name" in vals or "name_slugified" in vals:
            for rec in self:
                _debug.lifecycle(
                    "controller_page_menus_renamed",
                    page=rec.id,
                    menus=len(rec.menu_ids),
                    url=f"/model/{rec.name_slugified}",
                )
                rec.menu_ids.write(
                    {
                        "url": f"/model/{rec.name_slugified}",
                        "name": rec.name,
                    }
                )
        if "model_id" in vals:
            self._check_user_has_model_access()
        return res

    def unlink(self):
        views_to_delete = self.view_id.filtered(
            lambda v: v.controller_page_ids <= self and not v.inherit_children_ids
        )
        self -= views_to_delete.controller_page_ids
        _debug.lifecycle(
            "unlink", pages=self, count=len(self), views=len(views_to_delete)
        )
        views_to_delete.unlink()

        if self:
            self.env.registry.clear_cache("templates")
        return super().unlink()

    def open_website_url(self):
        url = f"/model/{self.name_slugified}"
        return {"type": "ir.actions.act_url", "url": url}
