# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from . import models
from . import wizard


from .const import VERIFACTU_INSTALLATION_SALT_PARAM


def _post_init_hook(env):
    env['ir.config_parameter'].sudo().set_str(VERIFACTU_INSTALLATION_SALT_PARAM, uuid.uuid4().hex)


def _uninstall_hook(env):
    env['ir.config_parameter'].sudo().search([('key', '=', VERIFACTU_INSTALLATION_SALT_PARAM)]).unlink()
