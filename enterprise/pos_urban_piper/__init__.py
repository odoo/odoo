from . import controllers
from . import models

import uuid


def _urban_piper_post_init(env):
    if not env['ir.config_parameter'].sudo().get_param('pos_urban_piper.uuid'):
        env['ir.config_parameter'].sudo().set_param('pos_urban_piper.uuid', str(uuid.uuid4()))
    en_US_language = env['res.lang'].sudo().search([('code', '=', 'en_US')], limit=1)
    if not en_US_language:
        en_US_language = env['res.lang'].with_context(active_test=False).sudo().search([('code', '=', 'en_US')], limit=1)
        env['base.language.install'].create({'lang_ids': [(6, 0, en_US_language.ids)]}).lang_install()
    env['ir.config_parameter'].sudo().set_param('pos_urban_piper.is_production_mode', 'True')
    if not env['ir.config_parameter'].sudo().get_param('pos_urban_piper.toggle_state'):
        env['ir.config_parameter'].sudo().set_param('pos_urban_piper.toggle_state', "")
