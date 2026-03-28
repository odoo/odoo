# Part of Odoo. See LICENSE file for full copyright and licensing details.
# The order of these tests is important, as the last one will uninstall this
# module. Ideally, the tests would be independent from one another but for now,
# ensure this order.

from . import test_crawl
from . import test_new_page_templates
from . import test_theme_scope
from . import test_theme_upgrade
# This test should be last.
from . import test_theme_standalone
