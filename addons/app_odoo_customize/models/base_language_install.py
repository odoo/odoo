# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class BaseLanguageInstall(models.TransientModel):
    _inherit = "base.language.install"
