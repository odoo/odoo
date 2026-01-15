# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

from odoo.cli.populate import Populate
from odoo.tests.common import tagged
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)


@tagged('-standard', 'pos_performance', '-at_install', 'post_install')
class TestPosPerformance(TestPointOfSaleHttpCommon):
    """
    These tests are designed for local performance testing only and will be skipped
    unless the 'pos_performance' tag is explicitly included in the test tags.

    To execute these tests locally, use the 'pos_performance' tag before the test name.
    Example:
        --test-tags pos_performance.test_pos_session_open_product_performance
    """

    def __populate_model(self, model_name, total_count):
        before_count = self.env[model_name].search_count([])
        if not before_count:
            return False
        populate_count = round(total_count / before_count) - 1
        Populate.populate(self.env, {model_name: populate_count}, 1)

        after_count = self.env[model_name].search_count([])
        _logger.info("\n\nBefore %s Count: %s\nAfter %s Count: %s\n\n", model_name, before_count, model_name, after_count)
        return True

    @mute_logger('odoo.models.unlink', 'odoo.cli.populate', 'odoo.tools.populate', 'odoo.tests.common', 'werkzeug')
    def test_pos_session_open_product_performance(self):
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', 20000)
        if not self.__populate_model('product.template', 20000):
            _logger.warning("The product.template model must contain at least one record before it can be populated.")
            return
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('tourSessionOpenProductPerformance', timeout=2000)
