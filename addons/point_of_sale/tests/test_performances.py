from unittest import skipIf

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

from odoo.cli.populate import Populate
from odoo.tests.common import tagged
from odoo.tools import mute_logger, config


@skipIf('pos_performance' not in config['test_tags'], "This test is intended for local performance testing of POS with a large dataset.")
@tagged('pos_performance', 'post_install', '-at_install')
class TestPosPerformance(TestPointOfSaleHttpCommon):

    def __populate_model(self, model_name, total_count):
        before_count = self.env[model_name].search_count([])
        populate_count = round(total_count / before_count) - 1
        Populate.populate(self.env, {model_name: populate_count}, 1)

        after_count = self.env[model_name].search_count([])
        print("====" * 25)
        print("Before Product Count: %s\nAfter Product Count: %s" % (before_count, after_count))
        print("====" * 25)

    @mute_logger('odoo.models.unlink', 'odoo.cli.populate', 'odoo.tools.populate', 'odoo.tests.common', 'werkzeug')
    def test_pos_session_opening(self):
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', 40000)
        self.__populate_model('product.template', 20000)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'tourSessionOpening', login="pos_user", timeout=1000)
        self.main_pos_config.current_session_id.close_session_from_ui()
