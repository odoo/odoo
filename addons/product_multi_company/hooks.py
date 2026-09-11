# Copyright 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.base_multi_company import hooks
except ImportError:
    _logger.info("Cannot find `base_multi_company` module in addons path.")


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Change access rule
    rule = env.ref("product.product_comp_rule")
    rule.write(
        {
            "domain_force": (
                "['|', ('company_ids', 'in', company_ids),"
                "('company_ids', '=', False)]"
            ),
        }
    )


def uninstall_hook(cr, registry):
    hooks.uninstall_hook(
        cr,
        "product.product_comp_rule",
    )
