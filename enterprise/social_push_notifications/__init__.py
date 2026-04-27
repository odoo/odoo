# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _create_social_accounts(env):
    """ This hook is used to add a default manufacture_pull_id, manufacture
    picking_type on every warehouse. It is necessary if the mrp module is
    installed after some warehouses were already created.
    """
    # TODO awa: check that no accounts are created yet
    env['website'].search([])._create_push_accounts()
