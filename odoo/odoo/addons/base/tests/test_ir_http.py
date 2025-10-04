import logging
import re
import time

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestIrHttpPerformances(TransactionCase):

    def test_routing_map_performance(self):
        self.env.registry.clear_cache('routing')
        # if the routing map was already generated it is possible that some compiled regex are in cache.
        # we want to mesure the cold state, when the worker just spawned, we need to empty the re cache
        re._cache.clear()

        self.env.registry.clear_cache('routing')
        start = time.time()
        self.env['ir.http'].routing_map()
        duration = time.time() - start
        _logger.info('Routing map web generated in %.3fs', duration)

        # generate the routing map of another website, to check if we can benefit from anything computed by the previous routing map
        start = time.time()
        self.env['ir.http'].routing_map(key=1)
        duration = time.time() - start
        _logger.info('Routing map website1 generated in %.3fs', duration)
