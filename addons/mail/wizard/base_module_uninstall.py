# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import base


class BaseModuleUninstall(base.BaseModuleUninstall):

    def _get_models(self):
        # consider mail-thread models only
        models = super(BaseModuleUninstall, self)._get_models()
        return models.filtered('is_mail_thread')
