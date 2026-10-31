from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def lazy_session_info(self):
        res = super().lazy_session_info()
        res['show_sale_receipts'] = self.env['ir.config_parameter'].sudo().get_bool('account.show_sale_receipts')
        return res

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        # `account` ships a public web interaction (the additional identifiers
        # composer on the website checkout) that uses `_t()`; without this, none
        # of its frontend terms are served, so the "+ Add identifier" label stays
        # in English whatever the website language is. Issue #299745.
        mods = super()._get_translation_frontend_modules_name()
        return mods + ["account"]
