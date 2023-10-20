# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes


def _post_init_hook(env):
    _preserve_tag_on_taxes(env)


def _preserve_tag_on_taxes(env):
    preserve_existing_tags_on_taxes(env, "l10n_lu_account")
