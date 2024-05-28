from odoo import models, fields
from odoo.exceptions import ValidationError

# TODO for this model, I should have default values that are +-$o-color-palettes
# And make sure the scss is good after creation.

# This model should be able to have more than 5 colors. Use one many2many field.

# This model should be able to handle the fact that the palette specifies the
# colors used for menu, footer, copyright, etc.


class WebsiteDesignPalette(models.Model):
    _name = 'website.design.palette'
    _description = 'Website Design Palette'

    name = fields.Char(string='Name')
    colors = fields.Many2many('website.design.color', string='Colors')

    def create(self, vals):
        for val in vals:
            val = self._handle_color(val)
        return super().create(vals)

    def write(self, vals):
        if 'colors' in vals:
            self.colors.unlink()
            vals = self._handle_color(vals)
        return super().write(vals)

    def _handle_color(self, val):
        # TODO: clean this function.
        colors_is_str = isinstance(val['colors'], str)
        if 'colors' not in val or len(val['colors']) < 2 or (colors_is_str and len(val['colors'].split(',')) < 2):
            raise ValidationError("A palette should have at least two colors.")
        if colors_is_str:
            val['colors'] = val['colors'].split(',')
            colors_records = [self.env['website.design.color'].create({
                'name': f'o-color-{i + 1}',
                'hex_value': color,
            }) for i, color in enumerate(val['colors'])]
            val['colors'] = colors_records
        if len(val['colors']) < 5:
            val['colors'] = self._make_palette(val['colors'][0], val['colors'][1])
        val['colors'] = [(6, 0, [color.id for color in val['colors']])]
        return val

    def _make_palette(self, color_1, color_2):
        # TODO: fix color are not calculated correctly.
        # Generate the palette with the same logic of `@function o-make-palette`.
        color_3_reference = self.env.ref('website.design_color_3_palette_generation')
        color_5_reference = self.env.ref('website.design_color_5_palette_generation')
        color_3, color_4, color_5 = self.env['website.design.color'].create([{
            'name': 'o-color-3',
            'hex_value': color_3_reference.get_modified_color(
                color_1.hue(),
                min(color_1.saturation(), color_3_reference.saturation())
            ),
        }, {
            'name': 'o-color-4',
            'hex_value': '#FFFFFF',
        }, {
            'name': 'o-color-5',
            'hex_value': color_5_reference.get_modified_color(
                color_1.hue(),
                min(color_1.saturation(), color_5_reference.saturation())
            ),
        }])
        # Check if primary/dark contrast is enough. If not adapt cc4 & cc5 schemes accordingly
        # TODO: how should I handle `o-cc{cc}-XXX` ?
        # if not self._has_enough_contrast(color_5, color_1):
        #     for cc in (4, 5):
        #         palette[f'o-cc{cc}-btn-primary'] = 'o-color-4'
        #         palette[f'o-cc{cc}-btn-secondary'] = 'o-color-2'
        #         palette[f'o-cc{cc}-text'] = 'o-color-3'
        #         palette[f'o-cc{cc}-link'] = 'o-color-4'

        # @if $-overrides-map {
        #     $-palette: map-merge($-palette, $-overrides-map);
        # }
        return [color_1, color_2, color_3, color_4, color_5]

    def _has_enough_contrast(self, color1, color2):
        # Check if the two colors have enough contrast.
        r = (max(color1.red(), color2.red())) - (min(color1.red(), color2.red()))
        g = (max(color1.green(), color2.green())) - (min(color1.green(), color2.green()))
        b = (max(color1.blue(), color2.blue())) - (min(color1.blue(), color2.blue()))
        sum_rgb = r + g + b
        return sum_rgb >= 300
