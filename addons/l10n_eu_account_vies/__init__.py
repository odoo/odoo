from . import controllers
from . import models


def uninstall_hook(env):
    """ Disable `vat_check_vies` for all companies """
    env['res.company'].search([('vat_check_vies', '=', True)]).vat_check_vies = False
