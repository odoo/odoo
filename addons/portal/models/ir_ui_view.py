# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class IrUiView(models.Model, base.IrUiView):

    customize_show = fields.Boolean("Show As Optional Inherit", default=False)
