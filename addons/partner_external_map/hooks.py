# Copyright 2015 Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

logger = logging.getLogger(__name__)


def set_default_map_settings(cr, registry):
    """Method called as post-install script
    The default method on the field can't be used, because it would be executed
    before loading map_website_data.xml, so it would not be able to set a
    value"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    user_model = env["res.users"]
    users = user_model.search([("context_map_website_id", "=", False)])
    logger.info("Updating user settings for maps...")
    users.write(
        {
            "context_map_website_id": user_model._default_map_website().id,
            "context_route_map_website_id": (
                user_model._default_route_map_website().id
            ),
        }
    )
    # Update the starting partner this way that is faster
    cr.execute(
        """
        UPDATE res_users
        SET context_route_start_partner_id = partner_id
        WHERE context_route_start_partner_id IS NULL;
        """
    )
