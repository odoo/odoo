from odoo import models, fields, api

NOT_DESIGN_FIELDS = ['id', 'display_name', 'create_uid', 'create_date', 'write_uid', 'write_date', 'website_id',
                     'forced_logo_height']

class WebsiteDesign(models.Model):
    _name = 'website.design'
    _description = 'Website Design'
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')

    # DESIGN VARIABLES

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

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            record._customize_design_variables(vals)
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

    def _filter_design_variables(self, vals):
        """
        Removes the keys in vals that are not design variables and replaces __
        by - in the keys to match the SCSS variable names.

        :param vals: dict of design variables to filter.
        :return: dict with only the keys that are design ones.
        """
        res = {}
        for key in vals:
            if key in NOT_DESIGN_FIELDS:
                continue
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
