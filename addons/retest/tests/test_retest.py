from openerp.tests import common
import os
import openerp.tools as tools
from openerp import modules
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class ReTest(common.TransactionCase):

    """Test againt modules like account, sale, purchase
    """

    def setUp(self):
        super(ReTest, self).setUp()

    def test_reload_test(self):
        if tools.config.options['test_enable']:
            cr, uid = self.cr, self.uid
            module_info = modules.load_information_from_description_file(
                "retest")
            for dat in module_info.get('depends', []):
                cr.commit()
                try:
                    mod_info = modules.load_information_from_description_file(
                        dat)
                    for test_module in mod_info.get('test', []):
                        pathname = os.path.join(dat, test_module)
                        fp = tools.file_open(pathname)
                        _logger.info(
                            "Try againt Test: {} of Module: {}".format(test_module, dat))
                        try:
                            tools.convert_yaml_import(
                                cr, dat, fp, kind="test", idref={}, mode="init")
                        except Exception:
                            _logger.exception(
                                'module %s: an exception occurred in a test', dat)
                finally:
                    if tools.config.options['test_commit']:
                        cr.commit()
                    else:
                        cr.rollback()
