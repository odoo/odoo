# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from pprint import pformat
from unittest.mock import patch

from odoo import http
from odoo.tests import tagged, TransactionCase

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class RoutesLinter(TransactionCase):

    def test_routes_definition(self):
        """Forbid redefinition of same-value attributes in an inherited route.

        Makes it easier to know what an inherited route really modifies and
        investigate unexpected behavior.
        """
        _check_and_complete_route_definition = http._check_and_complete_route_definition

        def extended_check(controller_cls, submethod, merged_routing):
            if 'type' in merged_routing:
                # merged_routing contains non default 'type' value
                # => current method is an inherited route.
                useless_overrides = {
                    key: value
                    for key, value in submethod.original_routing.items()
                    if key not in ('routes', 'type')
                    if merged_routing.get(key) == value
                }
                if useless_overrides:
                    _logger.warning(
                        "The endpoint %s is duplicating the existing routing configuration : %s",
                        f'{controller_cls.__module__}.{controller_cls.__name__}.{submethod.__name__}',
                        pformat(useless_overrides),
                    )

            _check_and_complete_route_definition(controller_cls, submethod, merged_routing)

        installed_modules = set(self.env['ir.module.module'].search([
            ('state', '=', 'installed'),
        ]).mapped('name'))
        with patch('odoo.http._check_and_complete_route_definition', extended_check):
            for _ in http._generate_routing_rules(installed_modules, nodb_only=False):
                pass
