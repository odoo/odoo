import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.json import scriptsafe as json_safe

logger = logging.getLogger(__name__)


class MixinWebsiteCover_Properties(models.AbstractModel):
    _name = "mixin.website.cover_properties"

    _description = "Cover Properties Website Mixin"

    cover_properties = fields.Text(
        default=lambda s: json_safe.dumps(s._default_cover_properties())
    )

    def _default_cover_properties(self):
        return {
            "background_color_class": "o_cc3",
            "background-image": "none",
            "opacity": "0.2",
            "resize_class": "o_half_screen_height",
        }

    def _load_cover_properties(self, raw):
        try:
            return json_safe.loads(raw)
        except ValueError, TypeError:
            logger.warning(
                "unparseable cover_properties on %s, falling back to defaults",
                self,
            )
            return self._default_cover_properties()

    def _get_background(self, height=None, width=None):
        self.check_singleton()
        properties = self._load_cover_properties(self.cover_properties)
        img = properties.get("background-image", "none")

        if img.startswith("url(/web/image/"):
            params = []
            if height is not None:
                params.append("height=%s" % height)
            if width is not None:
                params.append("width=%s" % width)
            if params:
                separator = "&" if "?" in img else "?"
                img = img[:-1] + separator + "&".join(params) + ")"
        return img

    def write(self, vals):
        if "cover_properties" not in vals:
            return super().write(vals)

        try:
            cover_properties = json_safe.loads(vals["cover_properties"])
        except ValueError, TypeError:
            raise ValidationError(_("Invalid cover properties value.")) from None
        resize_classes = cover_properties.get("resize_class", "").split()
        classes = ["o_half_screen_height", "o_full_screen_height", "cover_auto"]
        if not set(resize_classes).isdisjoint(classes):
            return super().write(vals)

        copy_vals = dict(vals)
        for item in self:
            old_cover_properties = self._load_cover_properties(item.cover_properties)
            cover_properties["resize_class"] = old_cover_properties.get(
                "resize_class", classes[0]
            )
            copy_vals["cover_properties"] = json_safe.dumps(cover_properties)
            super(MixinWebsiteCover_Properties, item).write(copy_vals)
        return True
