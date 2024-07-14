# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.modules.db
from . import models

import logging
_logger = logging.getLogger(__name__)


def post_init(env):
    # if not registry.has_unaccent: # FIXME: odoo/odoo#347
    if not odoo.modules.db.has_unaccent(env.cr):
        _logger.warning('pg extension "unaccent" not loaded, deduplication rules of type "accent" will be treated as "exact"')


def uninstall_hook(env):
    """ This method will remove all the server actions used for 'Merge Action' in the contextual menu. """
    models_to_clean = env['ir.model'].search([('ref_merge_ir_act_server_id', '!=', False)])
    actions_to_remove = models_to_clean.mapped('ref_merge_ir_act_server_id')
    actions_to_remove.unlink()
