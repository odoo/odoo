# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsitePagePropertiesBase(models.TransientModel):
    _name = 'website.page.properties.base'
    _description = "Page Properties Base"

    target_model_id = fields.Reference(selection='_selection_target_model_id', required=True)
    website_id = fields.Many2one('website', required=True)
    menu_ids = fields.One2many('website.menu', compute='_compute_menu_ids')
    is_in_menu = fields.Boolean(compute='_compute_is_in_menu', inverse='_inverse_is_in_menu')
    url = fields.Char(required=True)
    is_homepage = fields.Boolean(compute='_compute_is_homepage', inverse='_inverse_is_homepage', string='Homepage')
    can_publish = fields.Boolean(compute='_compute_can_publish')
    is_published = fields.Boolean(compute='_compute_is_published', inverse='_inverse_is_published')

    def _selection_target_model_id(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    def _get_menu_domain(self, url=None):
        self.ensure_one()
        target = self.target_model_id
        domain = [('website_id', '=', self.website_id.id)]
        url_to_check = url or self.url
        # For website pages, rely primarily on page_id as it stays stable
        # across URL changes. Fall back to URL for non-page targets.
        if target and target._name == 'website.page' and target.id:
            domain += ['|', ('page_id', '=', target.id), ('url', '=', url_to_check)]
        else:
            domain += [('url', '=', url_to_check)]
        return domain

    @api.depends('url', 'website_id')
    def _compute_menu_ids(self):
        for record in self:
            record.menu_ids = self.env['website.menu'].search(record._get_menu_domain())

    @api.depends('menu_ids')
    def _compute_is_in_menu(self):
        for record in self:
            record.is_in_menu = bool(record.menu_ids)

    def _inverse_is_in_menu(self):
        self.ensure_one()
        target = self.target_model_id
        if self.is_in_menu:
            if not self.menu_ids:
                self.env['website.menu'].create({
                    'name': target.name,
                    'url': self.url,
                    'parent_id': self.website_id.menu_id.id,
                    'website_id': self.website_id.id,
                    'page_id': target.id if (target and target._name == 'website.page') else False,
                })
        else:
            # If the page is no longer in menu, remove any relevant menu even
            # if `menu_ids` is empty due to URL changes in the same save.
            menus = self.menu_ids or self.env['website.menu'].search(self._get_menu_domain())
            if menus:
                menus.unlink()

    @api.depends('url', 'website_id.homepage_url')
    def _compute_is_homepage(self):
        for record in self:
            url = record.url
            current_homepage_url = record.website_id.homepage_url or '/'
            # If the url field matches the website's homepage_url, we know this
            # is the homepage.
            # However, the url field contains the url of the accessed route.
            # Therefore, being on '/' means we went through the homepage
            # controller and the request was rerouted.
            record.is_homepage = url == current_homepage_url or url == '/'

    def _inverse_is_homepage(self):
        self.ensure_one()
        url = self.url
        if self.is_homepage:
            if url and url != '/':
                self.website_id.homepage_url = url
        else:
            self.website_id.homepage_url = False

    @api.depends('target_model_id')
    def _compute_can_publish(self):
        for record in self:
            target = record.target_model_id
            if target._name == 'ir.ui.view':
                # Check we are in a non-custom state to avoid messing with
                # manually set values.
                record.can_publish = self._is_ir_ui_view_published(target) or self._is_ir_ui_view_unpublished(target)

                # FIXME disabled for the moment because it does not hide the url
                # in the sitemap and it is difficult to find a fix that would be
                # consistent. To revisit later.
                record.can_publish = False
            elif 'can_publish' in target._fields:
                record.can_publish = target.can_publish
            else:
                record.can_publish = False

    @api.depends('target_model_id')
    def _compute_is_published(self):
        for record in self:
            target = record.target_model_id
            if target._name == 'ir.ui.view':
                record.is_published = self._is_ir_ui_view_published(target)
            elif 'is_published' in target._fields:
                record.is_published = target.is_published
            else:
                record.is_published = False

    def _inverse_is_published(self):
        self.ensure_one()
        target = self.target_model_id
        if target._name == 'ir.ui.view':
            if self.can_publish:
                if self.is_published:
                    # Publish
                    target.visibility = ''
                    target.group_ids -= self._get_ir_ui_view_unpublish_group()
                else:
                    # Unpublish
                    target.visibility = 'restricted_group'
                    target.group_ids += self._get_ir_ui_view_unpublish_group()
                self.env.registry.clear_cache('templates')
        elif 'is_published' in target._fields:
            target.is_published = self.is_published

    def _get_ir_ui_view_unpublish_group(self):
        return self.env.ref('base.group_user')

    def _is_ir_ui_view_unpublished(self, view):
        view.ensure_one()
        return (view.visibility == 'restricted_group' and
                self._get_ir_ui_view_unpublish_group() in view.group_ids.all_implied_ids)

    def _is_ir_ui_view_published(self, view):
        view.ensure_one()
        return not view.visibility


class WebsitePageProperties(models.TransientModel):
    _name = 'website.page.properties'
    _description = "Page Properties"
    _inherit = [
        'website.page.properties.base',
    ]

    target_model_id = fields.Many2one('website.page')
    name = fields.Char(related='target_model_id.name', readonly=False)
    url = fields.Char(related='target_model_id.url', readonly=False)
    date_publish = fields.Datetime(related='target_model_id.date_publish', readonly=False)
    website_indexed = fields.Boolean(related='target_model_id.website_indexed', readonly=False)
    visibility = fields.Selection(related='target_model_id.visibility', readonly=False)
    visibility_password_display = fields.Char(related='target_model_id.visibility_password_display', readonly=False)
    group_ids = fields.Many2many(related='target_model_id.group_ids', readonly=False)
    is_new_page_template = fields.Boolean(related='target_model_id.is_new_page_template', readonly=False)

    old_url = fields.Char()
    redirect_old_url = fields.Boolean(default=False, store=False)
    redirect_type = fields.Selection(
        [
            ('301', '301 Moved permanently'),
            ('302', '302 Moved temporarily'),
        ],
        default='301',
        store=False,
        required=True,
    )

    @api.depends('url', 'website_id.homepage_url')
    def _compute_is_homepage(self):
        """
        Don't match is_homepage when url is '/' as this model's url is not the
        accessed route's url.
        """
        for record in self:
            url = record.url
            current_homepage_url = record.website_id.homepage_url or '/'
            record.is_homepage = url == current_homepage_url

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.old_url = record.url
        return records

    def write(self, vals):
        write_result = super().write(vals)

        # Once website.page has been written, the url might have been modified.
        # We can now create the redirects.
        if 'url' in vals:
            for record in self:
                old_url = record.old_url
                new_url = record.url
                if old_url != new_url:
                    if vals.get('redirect_old_url'):
                        website_id = vals.get('website_id') or record.website_id.id or False
                        self.env['website.rewrite'].create(
                            {
                                'name': vals.get('name') or record.name,
                                'redirect_type': vals.get('redirect_type') or record.redirect_type,
                                'url_from': old_url,
                                'url_to': new_url,
                                'website_id': website_id,
                            }
                        )
                    record.old_url = new_url

        return write_result
