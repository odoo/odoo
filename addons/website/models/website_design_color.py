import colorsys
import re

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WebsiteDesignColor(models.Model):
    _name = 'website.design.color'
    _description = "Website Design Color"

    name = fields.Char(string='Name', default='')
    hex_value = fields.Char(string='Hex Color Value')

    @api.constrains('hex_value')
    def _check_hex_value(self):
        pattern = "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
        for record in self:
            if not re.match(pattern, record.hex_value):
                raise ValidationError("Invalid hex color value.")

    def red(self):
        return int(self.hex_value[1:3], 16)

    def green(self):
        return int(self.hex_value[3:5], 16)

    def blue(self):
        return int(self.hex_value[5:7], 16)

    def hue(self):
        # Normalize RGB values
        r = self.red() / 255.0
        g = self.green() / 255.0
        b = self.blue() / 255.0
        # Convert RGB to HSL
        h, _, _ = colorsys.rgb_to_hls(r, g, b)
        # Convert hue value from range [0, 1] to [0, 360] degrees
        hue_degrees = h * 360
        return hue_degrees

    def saturation(self):
        r = self.red() / 255.0
        g = self.green() / 255.0
        b = self.blue() / 255.0
        # Convert RGB to HSL
        _, _, s = colorsys.rgb_to_hls(r, g, b)
        # Convert saturation value from range [0, 1] to [0, 100] percentage
        saturation_percentage = s * 100
        return saturation_percentage

    def get_modified_color(self, hue, saturation):
        # TODO: why this function doesn't returns the exact same values as
        # scss change-color() ?
        r = self.red() / 255
        g = self.green() / 255
        b = self.blue() / 255
        # Convert RGB to HSL
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        # Update hue and saturation
        h = (h + hue / 360) % 1.0
        s = max(0.0, min(1.0, s + saturation / 100))
        # Convert modified HSL color back to RGB
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        # Convert modified RGB color back to integers in the range [0, 255]
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
