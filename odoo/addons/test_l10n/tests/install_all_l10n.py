from odoo.tests import standalone


@standalone('all_l10n')
def test_all_l10n(env):
    """ This test will install all the l10n_* modules.
    As the module install is not yet fully transactional, the modules will
    remain installed after the test.
    """
    # Install the requirements
    l10n_mods = env['ir.module.module'].search([
        ('name', '=like', 'l10n_%'),
        ('state', '=', 'uninstalled'),
    ])
    l10n_mods.button_immediate_install()
