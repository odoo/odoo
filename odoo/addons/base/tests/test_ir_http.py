import logging
import re
import time

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestIrHttpPerformances(TransactionCase):

    def test_routing_map_performance(self):
        self.env.transaction.invalidate_ormcache('routing')
        # if the routing map was already generated it is possible that some compiled regex are in cache.
        # we want to mesure the cold state, when the worker just spawned, we need to empty the re cache
        re._cache.clear()

        self.env.transaction.invalidate_ormcache('routing')
        start = time.time()
        self.env['ir.http'].routing_map()
        duration = time.time() - start
        _logger.info('Routing map web generated in %.3fs', duration)

        # generate the routing map of another website, to check if we can benefit from anything computed by the previous routing map
        start = time.time()
        self.env['ir.http'].routing_map(key=1)
        duration = time.time() - start
        _logger.info('Routing map website1 generated in %.3fs', duration)


@tagged('-at_install', 'post_install')
class TestIrHttpConverters(TransactionCase):

    def test_models_converter_to_url(self):
        partners = self.env['res.partner'].create([
            {'name': 'Test Partner 1'},
            {'name': 'Test Partner 2'},
        ])
        converter = self.env['ir.http']._get_converters()['models'](None, 'res.partner')
        self.assertEqual(converter.to_url(partners), f"{partners[0].id},{partners[1].id}")
