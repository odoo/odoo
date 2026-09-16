from random import choice

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.libs.colors import (
    TAG_COLOR_INDICES,
    get_palette_color,
    hex_to_rgb,
    lighten_hex,
)
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinColor(models.AbstractModel):
    _name = "mixin.color"
    _description = "Color Behavior"

    _color_default_indices = TAG_COLOR_INDICES[1:]

    def _default_color(self):
        return choice(self._color_default_indices)

    def _check_hex_color_fields(self, *field_names, lengths=(3, 6)):
        for record in self:
            for field_name in field_names:
                value = record[field_name]
                if not value:
                    continue
                try:
                    if not value.startswith("#") or len(value) - 1 not in lengths:
                        raise ValueError(value)
                    hex_to_rgb(value)
                except ValueError:
                    _debug.logic(
                        "hex_color_rejected",
                        model=self._name,
                        field=field_name,
                        value=value,
                    )
                    raise ValidationError(
                        self.env._(
                            "%(field)s must be a hex color such as #2EB769.",
                            field=record._fields[field_name].string,
                        )
                    ) from None

    def _check_palette_color_fields(self, *field_names, palette):
        for record in self:
            for field_name in field_names:
                value = record[field_name]
                if not 0 <= value < len(palette):
                    _debug.logic(
                        "palette_color_rejected",
                        model=self._name,
                        field=field_name,
                        value=value,
                        palette=len(palette),
                    )
                    raise ValidationError(
                        self.env._(
                            "%(field)s must be a color index between 0 and %(max)s.",
                            field=record._fields[field_name].string,
                            max=len(palette) - 1,
                        )
                    )

    @api.model
    def _color_index_to_hex(self, value, *, palette, fallback=False):
        """Resolve an integer palette index; return fallback outside its range."""
        try:
            return get_palette_color(value, palette)
        except IndexError:
            _debug.logic(
                "palette_index_fallback",
                model=self._name,
                value=value,
                palette=len(palette),
            )
            return fallback

    @api.model
    def _lighten_color(self, color, factor):
        return lighten_hex(color, factor)
