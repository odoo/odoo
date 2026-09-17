import functools
from base64 import b64encode
from datetime import UTC

from odoo import api, fields, models
from odoo.libs.colors import get_hsl_from_seed
from odoo.libs.debug_log import DebugLog
from odoo.tools import file_open, html_escape
from odoo.tools.misc import limited_field_access_token

_FieldName = str


_debug = DebugLog(__name__)


@functools.cache
def _get_placeholder_image(path: str) -> bytes:
    with file_open(path, "rb") as file:
        data = file.read()
    _debug.perf.count("placeholder_image_loaded", path=path, bytes=len(data))
    return data


class MixinAvatar(models.AbstractModel):
    _name = "mixin.avatar"
    _inherit = ["mixin.image"]
    _description = "Avatar Mixin"
    _avatar_name_field = "name"
    _avatar_extra_depends: tuple[str, ...] = ()

    avatar_1920 = fields.Image(
        string="Avatar",
        compute="_compute_avatar_1920",
    )
    avatar_1024 = fields.Image(compute="_compute_avatar_1024")
    avatar_512 = fields.Image(compute="_compute_avatar_512")
    avatar_256 = fields.Image(compute="_compute_avatar_256")
    avatar_128 = fields.Image(compute="_compute_avatar_128")

    @api.depends(
        lambda self: [
            self._avatar_name_field,
            "image_1920",
            *self._avatar_extra_depends,
        ]
    )
    def _compute_avatar_1920(self) -> None:
        self._update_avatar("avatar_1920", "image_1920")

    @api.depends(
        lambda self: [
            self._avatar_name_field,
            "image_1024",
            *self._avatar_extra_depends,
        ]
    )
    def _compute_avatar_1024(self) -> None:
        self._update_avatar("avatar_1024", "image_1024")

    @api.depends(
        lambda self: [self._avatar_name_field, "image_512", *self._avatar_extra_depends]
    )
    def _compute_avatar_512(self) -> None:
        self._update_avatar("avatar_512", "image_512")

    @api.depends(
        lambda self: [self._avatar_name_field, "image_256", *self._avatar_extra_depends]
    )
    def _compute_avatar_256(self) -> None:
        self._update_avatar("avatar_256", "image_256")

    @api.depends(
        lambda self: [self._avatar_name_field, "image_128", *self._avatar_extra_depends]
    )
    def _compute_avatar_128(self) -> None:
        self._update_avatar("avatar_128", "image_128")

    def _update_avatar(self, avatar_field: _FieldName, image_field: _FieldName) -> None:
        fallbacks = 0  # debuglog
        for record in self:
            avatar = record[image_field]
            if not avatar:
                fallbacks += 1  # debuglog
                name = record[record._avatar_name_field]
                generated = bool(record.id and name and name.strip())
                _debug.logic(
                    "avatar_fallback",
                    model=record._name,
                    record=record.id,
                    field=avatar_field,
                    source="initials" if generated else "placeholder",
                )
                if generated:
                    avatar = record._prepare_avatar_svg()
                else:
                    avatar = b64encode(record._get_avatar_placeholder())
            record[avatar_field] = avatar
        _debug.perf.count(
            "avatar_updated",
            model=self._name,
            field=avatar_field,
            records=len(self),
            fallbacks=fallbacks,
        )

    def _prepare_avatar_svg(self) -> bytes:
        self.check_singleton()
        initial = html_escape(self[self._avatar_name_field].strip()[0].upper())
        _debug.logic(
            "avatar_svg_generated",
            model=self._name,
            record=self.id,
            initial=initial,
            seeded_by_date=bool(self.create_date),
        )
        bgcolor = get_hsl_from_seed(
            self[self._avatar_name_field]
            + str(
                self.create_date.replace(tzinfo=UTC).timestamp()
                if self.create_date
                else ""
            )
        )
        return b64encode(
            (
                '<?xml version="1.0" encoding="UTF-8" ?>'
                '<svg height="180" width="180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
                f'<rect fill="{bgcolor}" height="180" width="180"/>'
                f'<text fill="#ffffff" font-size="96" text-anchor="middle" x="90" y="125" font-family="sans-serif">{initial}</text>'
                "</svg>"
            ).encode()
        )

    def _get_avatar_placeholder_path(self) -> str:
        return "base/static/img/avatar_grey.png"

    def _get_avatar_placeholder(self) -> bytes:
        return _get_placeholder_image(self._get_avatar_placeholder_path())

    def _get_avatar_128_access_token(self) -> str:
        self.check_singleton()
        return limited_field_access_token(self, "avatar_128", scope="binary")
