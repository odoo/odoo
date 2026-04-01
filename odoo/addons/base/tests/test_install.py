from unittest import SkipTest

from odoo.tests.common import standalone
from odoo.tests.test_module_operations import install
from odoo.tools import mute_logger
from odoo.tools.convert import ParseError


@standalone('test_isolated_install')
def test_isolated_install(env):
    """ This test checks that a module failing to install has no side effect on
    other modules.  In particular, the module that was installed just before is
    correctly marked as 'installed'.
    """
    MODULE_NAMES = ['test_install_base', 'test_install_auto', 'test_install_fail']
    modules = {
        module.name: module
        for module in env['ir.module.module'].search([('name', 'in', MODULE_NAMES)])
    }
    if len(modules) < 3:
        raise SkipTest(f"Failed to find the required modules {MODULE_NAMES}")
    if not all(module.state == 'uninstalled' for module in modules.values()):
        raise SkipTest(f"The modules {MODULE_NAMES} should not be installed")

    # now install test_install_fail, which should install test_install_base and
    # test_install_auto just before it
    try:
        with mute_logger('odoo.modules.registry'):
            install(env.cr.dbname, modules['test_install_fail'].id, 'test_install_fail')
    except ParseError:
        pass

    # make sure to reset the transaction
    env.cr.rollback()
    env.transaction.reset()

    # check the presence of the cron
    cron = env['ir.cron'].search([('cron_name', '=', 'test_install_auto_cron')])
    assert cron, "The cron 'test_install_auto_cron' has not been created"

    # check the states of the modules
    assert modules['test_install_base'].state == 'installed', "Module 'test_install_base' not installed"
    assert modules['test_install_auto'].state == 'installed', "Module 'test_install_auto' not installed"
    assert modules['test_install_fail'].state == 'uninstalled', "Module 'test_install_fail' should be uninstalled"

    # check that test_install_auto's code is present
    assert env['res.currency']._test_install_auto_cron() is True, "Cron code not working"
