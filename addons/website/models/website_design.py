from odoo import models, fields, api

NOT_DESIGN_FIELDS = ['id', 'display_name', 'create_uid', 'create_date', 'write_uid', 'write_date', 'website_id',
                     'forced_logo_height']


class WebsiteDesign(models.Model):
    _name = 'website.design'
    _description = 'Website Design'
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')

    # DESIGN VARIABLES

    layout = fields.Many2one('website.design.option', string='Layout', default=lambda self: self.env.ref('website.design_option_layout_full'))
    footer__template = fields.Many2one('website.design.option', string='Footer Template', default=lambda self: self.env.ref('website.design_option_footertemplate_default'))
    footer__effect = fields.Many2one('website.design.option', string='Footer Effect', default=lambda self: self.env.ref('website.design_option_footereffect_none'))
    btn__ripple = fields.Many2one('website.design.option', string='Button Ripple', default=lambda self: self.env.ref('website.design_option_btnripple_false'))
    header__scroll__effect = fields.Many2one('website.design.option', string='Header Scroll Effect', default=lambda self: self.env.ref('website.design_option_headerscrolleffect_standard'))
    link__underline = fields.Many2one('website.design.option', string='Link Underline', default=lambda self: self.env.ref('website.design_option_linkunderline_hover'))
    header__template = fields.Many2one('website.design.option', string='Header Template', default=lambda self: self.env.ref('website.design_option_headertemplate_default'))
    header__links__style = fields.Many2one('website.design.option', string='Header Links Style', default=lambda self: self.env.ref('website.design_option_headerlinksstyle_default'))
    hamburger__position = fields.Many2one('website.design.option', string='Hamburger Position', default=lambda self: self.env.ref('website.design_option_hamburgerposition_left'))
    hamburger__position__mobile = fields.Many2one('website.design.option', string='Hamburger Position Mobile', default=lambda self: self.env.ref('website.design_option_hamburgerpositionmobile_left'))

    # If the website design is deleted, we should delete all website fonts ?

    font = fields.Many2one('website.design.font', string='Font')
    headings__font = fields.Many2one('website.design.font', string='Headings Font')
    navbar__font = fields.Many2one('website.design.font', string='Navbar Font')
    buttons__font = fields.Many2one('website.design.font', string='Buttons Font')

    # Colors
    # This should be a Many2one field to website.design.palette
    color__palettes__name = fields.Char(string='Color Palettes Name', default='base-1')

    paragraph__margin__top = fields.Char(string='Paragraph Margin Top', default='0')
    paragraph__margin__bottom = fields.Char(string='Paragraph Margin Bottom', default='16px')

    display__1__font__size = fields.Char(string='Display 1 Font Size', default='5rem')
    display__2__font__size = fields.Char(string='Display 2 Font Size', default='4.5rem')
    display__3__font__size = fields.Char(string='Display 3 Font Size', default='4rem')
    display__4__font__size = fields.Char(string='Display 4 Font Size', default='3.5rem')

    btn__primary__outline__border__width = fields.Char(string='Primary Button Outline Border Width', default='1px')
    btn__secondary__outline__border__width = fields.Char(string='Secondary Button Outline Border Width', default='1px')
    btn__padding__y = fields.Char(string='Button Padding Y', default='6px')
    btn__padding__x = fields.Char(string='Button Padding X', default='16px')
    btn__font__size = fields.Char(string='Button Font Size', default='16px')
    btn__padding__y__sm = fields.Char(string='Button Padding Y SM', default='1px')
    btn__padding__x__sm = fields.Char(string='Button Padding X SM', default='8px')
    btn__font__size__sm = fields.Char(string='Button Font Size SM', default='12px')
    btn__padding__y__lg = fields.Char(string='Button Padding Y LG', default='16px')
    btn__padding__x__lg = fields.Char(string='Button Padding X LG', default='40px')
    btn__font__size__lg = fields.Char(string='Button Font Size LG', default='20px')
    btn__border__radius = fields.Char(string='Button Border Radius', default='6.4px')
    btn__border__radius__sm = fields.Char(string='Button Border Radius SM', default='4.8px')
    btn__border__radius__lg = fields.Char(string='Button Border Radius LG', default='32px')
    btn__border__width = fields.Char(string='Button Border Width', default='2px')
    btn__primary__flat = fields.Boolean(string='Primary Button Flat', default=False)
    btn__secondary__flat = fields.Boolean(string='Secondary Button Flat', default=False)
    btn__primary__outline = fields.Boolean(string='Primary Button Outline', default=False)
    btn__secondary__outline = fields.Boolean(string='Secondary Button Outline', default=False)

    input__padding__y = fields.Char(string='Input Padding Y', default='6px')
    input__padding__x = fields.Char(string='Input Padding X', default='12px')
    input__font__size = fields.Char(string='Input Font Size', default='16px')
    input__padding__y__sm = fields.Char(string='Input Padding Y SM', default='4px')
    input__padding__x__sm = fields.Char(string='Input Padding X SM', default='8px')
    input__font__size__sm = fields.Char(string='Input Font Size SM', default='12px')
    input__padding__y__lg = fields.Char(string='Input Padding Y LG', default='8px')
    input__padding__x__lg = fields.Char(string='Input Padding X LG', default='16px')
    input__font__size__lg = fields.Char(string='Input Font Size LG', default='20px')
    input__border__width = fields.Char(string='Input Border Width', default='1px')
    # TODO: check why we don't have input_border_width_sm and input_border_width_lg
    input__border__radius = fields.Char(string='Input Border Radius', default='6.4px')
    input__border__radius__sm = fields.Char(string='Input Border Radius SM', default='4.8px')
    input__border__radius__lg = fields.Char(string='Input Border Radius LG', default='9.6px')

    headings__line__height = fields.Char(string='Headings Line Height', default='1.2')
    headings__margin__top = fields.Char(string='Headings Margin Top', default='0')
    headings__margin__bottom = fields.Char(string='Headings Margin Bottom', default='0.5rem')

    footer__scrolltop = fields.Boolean(string='Footer Scrolltop', default=False)
    header__font__size = fields.Char(string='Header Font Size', default='1rem')
    menu__border__width = fields.Char(string='Menu Border Width', default='null')
    # Maybe menu-border-style should be a selection field
    menu__border__style = fields.Char(string='Menu Border Style', default='solid')
    menu__border__radius = fields.Char(string='Menu Border Radius', default='null')
    menu__box__shadow = fields.Char(string='Menu Box Shadow', default='null')

    body__line__height = fields.Char(string='Body Line Height', default='1.5')
    # Logo height requires two fields because it can be computed based on the
    # base font size or forced to a specific value.
    logo__height = fields.Char(
        string='Logo Height',
        compute='_compute_logo_height',
        inverse='_inverse_logo_height',
        default='null',
    )
    forced_logo_height = fields.Char(string='Forced Logo Height', default='null')
    font__size__base = fields.Char(string='Font Size Base', default='1rem')

    sidebar__width = fields.Char(string='Sidebar Width', default='18.75rem')

    def write(self, vals):
        for key in vals:
            comodel = self._fields[key].comodel_name
            if comodel and comodel.startswith('website.design.'):
                if isinstance(vals[key], int):
                    vals[key] = self.env[comodel].browse(vals[key])
                elif vals[key] == 'null' or vals[key] == 'false':
                    vals[key] = False
                elif isinstance(vals[key], str):
                    vals[key] = self.env[comodel].browse(int(vals[key]))
            elif self._fields[key].type == 'boolean' and isinstance(vals[key], str):
                vals[key] = vals[key] == 'true'
        res = super().write(vals)
        for record in self:
            record._customize_design_variables(vals.copy())

        def handle_design_options(self, vals, attribute):
            for key in vals:
                if self._fields[key].comodel_name != 'website.design.option':
                    continue

                items_to_activate = self.with_context(active_test=False).mapped(key).mapped(attribute).mapped('key') or []
                unactive_design_options = self.env['website.design.option'].search([
                    ('name', '=', vals[key].name),
                    ('value', '!=', vals[key].value),
                ])
                items_to_deactivate = []
                for unactive_design_option in unactive_design_options:
                    items_to_deactivate.extend(unactive_design_option.with_context(active_test=False).mapped(attribute).mapped('key') or [])
                items_to_deactivate = list(set(items_to_deactivate) - set(items_to_activate))
                if len(items_to_activate) or len(items_to_deactivate):
                    # Force the website in context to ensure the COW.
                    self.env['website'].with_context(website_id=self.env['website'].get_current_website().id)\
                        .theme_customize_data(attribute == 'views_to_activate', items_to_activate, items_to_deactivate)

        # Update the views for design.option records.
        handle_design_options(self, vals, 'views_to_activate')

        # Update the assets for design.option records.
        handle_design_options(self, vals, 'assets_to_activate')

        return res

    @api.model_create_multi
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            default_style_vals = {field: record[field] for field in record._fields}
            record._customize_design_variables(default_style_vals)
        return records

    def _customize_design_variables(self, vals):
        """
        Customizes design variables.

        :param vals: dict of design variables to customize. The keys are the
            field names / SCSS variable names and the values are the new values.
        """
        if self.env.context.get('skip_customize_scss'):
            return
        vals = self._filter_design_variables(vals)
        self.env['web_editor.assets']\
            .with_context(website_id=self.website_id.id)\
            .make_scss_customization('/website/static/src/scss/options/user_values.scss', vals)

    def _filter_design_variables(self, vals): # TODO rename this function
        """
        Removes the keys in vals that are not design variables, replaces `__`
        by `-` in the keys to match the SCSS variable names and compute the
        values for field that are design options.

        :param vals: dict of design variables to filter.
        :return: dict with only the keys that are design ones.
        """
        res = {}
        # Maybe I should write on google{Local}Fonts only on font changes ?
        google_local_fonts = (f"'{font.name}': '{font.attachment_id or ''}'" for font in self.env['website.design.font'].search([('is_local', '=', True), ('website_id', 'in', [False, self.website_id.id])]))
        res['google-local-fonts'] = 'null' if not google_local_fonts else f"({', '.join(list(google_local_fonts))})"
        google_fonts = (f"'{font.name}'" for font in self.env['website.design.font'].search([('is_local', '=', False), ('website_id', 'in', [False, self.website_id.id])]))
        res['google-fonts'] = 'null' if not google_fonts else f"({', '.join(list(google_fonts))})"
        for key in vals:
            if key in NOT_DESIGN_FIELDS:
                continue
            if self._fields[key].comodel_name == 'website.design.option':
                # Compute the value of the design option.
                vals[key] = vals[key].value
            if self._fields[key].type == 'boolean':
                vals[key] = 'true' if vals[key] else 'false'
            if self._fields[key].comodel_name == 'website.design.font':
                if not vals[key] or (isinstance(vals[key], str) and vals[key]) == '()':
                    vals[key] = 'null'
                elif not isinstance(vals[key], str):
                    vals[key] = f"'{vals[key].name}'"
            # As python variable names cannot contains dashes, we replace them
            # by double underscores.
            res[key.replace('__', '-')] = vals[key]
        return res

    # Variables specific functions

    @api.depends('forced_logo_height', 'font__size__base')
    def _compute_logo_height(self):
        """
        Computes the logo height based on the font size or the forced height.
        """
        for record in self:
            if record.forced_logo_height != 'null':
                record.with_context(skip_customize_scss=True).logo__height = record.forced_logo_height
                return
            font_size_base = float(record.font__size__base.replace('rem', ''))
            # $font-size-base * $line-height-base + $nav-link-padding-y * 2;
            record.with_context(skip_customize_scss=True).logo__height = str(font_size_base * 1.5 + 0.5 * 2) + 'rem'

    def _inverse_logo_height(self):
        """Sets the forced logo height to the current logo height."""
        for record in self:
            record.with_context(skip_customize_scss=True).forced_logo_height = record.logo__height
