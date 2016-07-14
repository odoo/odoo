# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class BaseGengoTranslations(models.TransientModel):
    _inherit = 'base.gengo.translations'
    # update GROUPS, that are the groups allowing to access the gengo key.
    # this is done here because in the base_gengo module, the various website
    # groups do not exist, limiting the access to the admin group.
    GROUPS = ['base.group_website_designer', 'base.group_website_publisher']
