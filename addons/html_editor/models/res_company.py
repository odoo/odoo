import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

HEX_COLOR_REGEX = re.compile(r'#[0-9A-F]{6}([0-9A-F]{2})?')


class ResCompany(models.Model):
    _inherit = 'res.company'

    favorite_colors = fields.Json(
        string="Favorite Colors",
        help="Colors of the company branding, offered by the color pickers of the editor.",
    )

    # Dedicated methods, rather than `write`, as the web client reloads after
    # any `write` on a company (see `ReloadCompanyPlugin`), which would close
    # the editor in which the color is picked.

    def add_favorite_color(self, color):
        """Add a color to the favorite colors of the company, unless already
        there.

        :param str color: hexadecimal color
        :return: the favorite colors of the company
        :rtype: list[str]
        """
        self.ensure_one()
        color = str(color).upper()
        colors = self.favorite_colors or []
        if color not in colors:
            self.favorite_colors = [*colors, color]
        return self.favorite_colors

    def remove_favorite_color(self, color):
        """Remove a color from the favorite colors of the company.

        :param str color: hexadecimal color
        :return: the favorite colors of the company
        :rtype: list[str]
        """
        self.ensure_one()
        color = str(color).upper()
        colors = self.favorite_colors or []
        if color in colors:
            self.favorite_colors = [c for c in colors if c != color]
        return self.favorite_colors or []

    @api.constrains('favorite_colors')
    def _check_favorite_colors(self):
        for company in self:
            colors = company.favorite_colors or []
            if not isinstance(colors, list) or not all(
                isinstance(color, str) and HEX_COLOR_REGEX.fullmatch(color) for color in colors
            ):
                raise ValidationError(self.env._(
                    "The favorite colors must be a list of uppercase hexadecimal colors, such as #FF0000."
                ))
