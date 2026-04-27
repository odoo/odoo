from odoo import models

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(Http, cls)._get_translation_frontend_modules_name()
        return mods + ['room']
