# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval
from odoo import api, fields, models


class WebsiteControllerPage(models.Model):
    _name = 'website.controller.page'
    _inherits = {'ir.ui.view': 'view_id'}
    _inherit = [
        'website.published.multi.mixin',
        'website.searchable.mixin',
    ]
    _description = 'Model Page'
    _order = 'website_id, id DESC'
    _sql_constraints = [
        ('unique_name_slugified', 'UNIQUE(name_slugified)', 'url should be unique')
    ]

    view_id = fields.Many2one('ir.ui.view', string='Listing view', required=True, ondelete="cascade")
    record_view_id = fields.Many2one('ir.ui.view', string='Record view', ondelete="cascade")
    menu_ids = fields.One2many('website.menu', 'controller_page_id', 'Related Menus')

    website_id = fields.Many2one(related='view_id.website_id', store=True, readonly=False, ondelete='cascade')

    name = fields.Char(string="The name is used to generate the URL and is shown in the browser title bar",
        compute="_compute_name",
        inverse="_inverse_name",
        required=True,
        store=True)
    # Bindings to model/records, to expose the page on the website.
    # Route: /model/<string:page_name_slugified>
    name_slugified = fields.Char(compute="_compute_name_slugified", store=True,
        string="URL", help="The name of the page usable in a URL", inverse="_inverse_name_slugified")
    url_demo = fields.Char(string="Demo URL", compute="_compute_url_demo")

    record_domain = fields.Char(string="Domain", help="Domain to restrict records that can be viewed publicly")
    default_layout = fields.Selection(
        selection=[
            ('grid', "Grid"),
            ('list', "List"),
        ],
        default="grid",
    )

    @api.constrains('view_id', 'model_id', "model")
    def _check_user_has_model_access(self):
        for record in self:
            self.env[record.model_id.model].check_access('read')

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
            rec.name_slugified = self.env['ir.http']._slugify(rec.name or '')

    def _inverse_name_slugified(self):
        for rec in self:
            rec.name_slugified = self.env['ir.http']._slugify(rec.name_slugified)

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

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec.menu_ids.write({
                "url": f"/model/{rec.name_slugified}",
                "name": rec.name,
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
        return {
            "type": "ir.actions.act_url",
            "url": url
        }
