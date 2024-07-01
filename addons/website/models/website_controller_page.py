# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo.addons.http_routing.models.ir_http import slugify, slug
from odoo import api, fields, models


class WebsiteControllerPage(models.Model):
    _name = 'website.controller.page'
    _inherits = {'ir.ui.view': 'view_id'}
    _inherit = [
        'website.published.multi.mixin',
        'website.searchable.mixin',
    ]
    _description = 'Model Page'
    _order = 'website_id'

    view_id = fields.Many2one('ir.ui.view', string='View', required=True, ondelete="cascade")
    menu_ids = fields.One2many('website.menu', 'controller_page_id', 'Related Menus')

    website_id = fields.Many2one(related='view_id.website_id', store=True, readonly=False, ondelete='cascade')

    # Bindings to model/records, to expose the page on the website.
    # Route: /model/<string:page_name_slugified>
    page_name = fields.Char(string="Name", help="The name is used to generate the URL and is shown in the browser title bar", required=True)
    name_slugified = fields.Char(compute="_compute_name_slugified", store=True,
        string="URL", help="The name of the page usable in a URL", inverse="_inverse_name_slugified")
    url_demo = fields.Char(string="Demo URL", compute="_compute_url_demo")
    page_type = fields.Selection(selection=[("listing", "Listing"), ("single", "Single record")],
        default="listing", string="Page Type",
        help="The type of the page. If set, it indicates whether the page displays a list of records or a single record")
    record_domain = fields.Char(string="Domain", help="Domain to restrict records that can be viewed publicly")
    default_layout = fields.Selection(
        selection=[
            ('grid', "Grid"),
            ('list', "List"),
        ],
        default="grid",
    )

    _sql_constraints = [
        ('unique_name_slugified', 'UNIQUE(page_type, name_slugified)', 'url should be unique')
    ]

    @api.constrains('view_id', 'model_id', "model")
    def _check_user_has_model_access(self):
        for record in self:
            self.env[record.model_id.model].check_access_rights('read')

    @api.depends("model_id", "page_name")
    def _compute_name_slugified(self):
        for rec in self:
            if not rec.model_id or not rec.page_type:
                rec.name_slugified = False
                continue
            rec.name_slugified = slugify(rec.page_name or '')

    def _inverse_name_slugified(self):
        for rec in self:
            rec.name_slugified = slugify(rec.name_slugified)

    @api.depends("name_slugified")
    def _compute_url_demo(self):
        for rec in self:
            if not rec.name_slugified:
                rec.url_demo = ""
                continue
            url = ["", "model", rec.name_slugified]
            if rec.page_type == "single":
                url.append("record-slug-[id]")
            rec.url_demo = "/".join(url)

    def write(self, vals):
        res = super().write(vals)
        self.menu_ids.write({
            "url": f"/model/{self.name_slugified}",
            "name": self.page_name,
        })
        return res

    def unlink(self):
        # When a website_controller_page is deleted, the ORM does not delete its
        # ir_ui_view. So we got to delete it ourself, but only if the
        # ir_ui_view is not used by another website_page.
        views_to_delete = self.view_id.filtered(
            lambda v: v.controller_page_ids <= self and not v.inherit_children_ids
        )
        # Rebind self to avoid unlink already deleted records from `ondelete="cascade"`
        self = self - views_to_delete.controller_page_ids
        views_to_delete.unlink()

        # Make sure website._get_menu_ids() will be recomputed
        self.env.registry.clear_cache()
        return super().unlink()

    def open_website_url(self):
        url = f"/model/{self.name_slugified}"
        if self.page_type == "single":
            rec = self.env[self.model_id.model].search(literal_eval(self.record_domain or "[]"), limit=1)
            if rec:
                url += f"/{slug(rec)}"
        return {
            "type": "ir.actions.act_url",
            "url": url
        }
