# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid


from odoo import fields, models


class PosSession(models.Model):
    _inherit = "pos.session"

    access_token = fields.Char(
        "Unique identifier of the pos session",
        copy=False,
        required=True,
        readonly=True,
        default=lambda self: self._get_access_token(),
    )

    @staticmethod
    def _get_access_token():
        return uuid.uuid4().hex[:8]
