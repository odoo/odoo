# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from hashlib import sha512
from odoo import models, fields, api
from odoo.tools import html_escape, file_open
from odoo.tools.misc import limited_field_access_token


def get_random_ui_color_from_seed(seed):
    hashed_seed = sha512(seed.encode()).hexdigest()
    # Colors from COLOR_XL[] in core/colors/colors.js
    avatar_bg_colors = ["#4EA7F2", "#3188E6", "#056BD9", "#155193", "#A76DBC", "#7F4295", "#6D2387", "#4F1565", "#EA6175", "#CE4257", "#982738", "#791B29", "#43C5B1", "#00A78D", "#0E8270", "#105F53", "#F4A261", "#F48935", "#BE5D10", "#7D380D", "#8481DD", "#5752D1", "#3A3580", "#26235F", "#A4A8B6", "#7E8290", "#545B70", "#3F4250", "#FFD86D", "#FFBC2C", "#C08A16", "#936A12"]
    num = int(hashed_seed, 16)
    return avatar_bg_colors[num % len(avatar_bg_colors)]


class AvatarMixin(models.AbstractModel):
    _name = 'avatar.mixin'
    _inherit = ['image.mixin']
    _description = "Avatar Mixin"
    _avatar_name_field = "name"

    # all image fields are base64 encoded and PIL-supported
    avatar_1920 = fields.Image("Avatar", compute="_compute_avatar_1920")
    avatar_1024 = fields.Image("Avatar 1024", compute="_compute_avatar_1024")
    avatar_512 = fields.Image("Avatar 512", compute="_compute_avatar_512")
    avatar_256 = fields.Image("Avatar 256", compute="_compute_avatar_256")
    avatar_128 = fields.Image("Avatar 128", compute="_compute_avatar_128")

    def _compute_avatar(self, avatar_field, image_field):
        for record in self:
            avatar = record[image_field]
            if not avatar:
                if record.id and record[record._avatar_name_field]:
                    avatar = record._avatar_generate_svg()
                else:
                    avatar = b64encode(record._avatar_get_placeholder())
            record[avatar_field] = avatar

    @api.depends(lambda self: [self._avatar_name_field, 'image_1920'])
    def _compute_avatar_1920(self):
        self._compute_avatar('avatar_1920', 'image_1920')

    @api.depends(lambda self: [self._avatar_name_field, 'image_1024'])
    def _compute_avatar_1024(self):
        self._compute_avatar('avatar_1024', 'image_1024')

    @api.depends(lambda self: [self._avatar_name_field, 'image_512'])
    def _compute_avatar_512(self):
        self._compute_avatar('avatar_512', 'image_512')

    @api.depends(lambda self: [self._avatar_name_field, 'image_256'])
    def _compute_avatar_256(self):
        self._compute_avatar('avatar_256', 'image_256')

    @api.depends(lambda self: [self._avatar_name_field, 'image_128'])
    def _compute_avatar_128(self):
        self._compute_avatar('avatar_128', 'image_128')

    def _avatar_generate_svg(self):
        initial = html_escape(self[self._avatar_name_field][0].upper())
        bgcolor = get_random_ui_color_from_seed(self[self._avatar_name_field] + str(self.create_date.timestamp() if self.create_date else ""))
        return b64encode((
            "<?xml version='1.0' encoding='UTF-8' ?>"
            "<svg height='180' width='180' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>"
            f"<rect fill='{bgcolor}' height='180' width='180'/>"
            f"<text fill='#ffffff' font-size='96' text-anchor='middle' x='90' y='125' font-family='sans-serif'>{initial}</text>"
            "</svg>"
        ).encode())

    def _avatar_get_placeholder_path(self):
        return "base/static/img/avatar_grey.png"

    def _avatar_get_placeholder(self):
        with file_open(self._avatar_get_placeholder_path(), 'rb') as f:
            return f.read()

    def _get_avatar_128_access_token(self):
        """Return a scoped access token for the `avatar_128` field. The token can be
        used with `ir_binary._find_record` to bypass access rights.

        :rtype: str
        """
        self.ensure_one()
        return limited_field_access_token(self, "avatar_128", scope="binary")
