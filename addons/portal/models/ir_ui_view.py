# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons import web, mail, web_editor


class IrUiView(web.IrUiView, web_editor.IrUiView, mail.IrUiView):

    customize_show = fields.Boolean("Show As Optional Inherit", default=False)
