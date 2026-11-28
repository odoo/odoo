from odoo import models
from odoo.http import request

CONTEXT_KEYS = ['editable', 'edit_translations', 'translatable']


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_editor_context(cls):
        """ Check for ?editable and stuff in the query-string """
        return {
            key: True
            for key in CONTEXT_KEYS
            if key in request.httprequest.args and key not in request.env.context
        }

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        ctx = cls._get_editor_context()
        request.update_context(**ctx)

    def session_info(self):
        session_info = super().session_info()
        if user_companies := session_info.get('user_companies'):
            allowed_companies = user_companies['allowed_companies']
            companies_sudo = self.env['res.company'].sudo().browse(list(allowed_companies))
            for company in companies_sudo:
                allowed_companies[company.id]['favorite_colors'] = company.favorite_colors or []
        return session_info

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        return ['html_editor', *super()._get_translation_frontend_modules_name()]
