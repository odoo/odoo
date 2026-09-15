from odoo import models
from odoo.libs.debug_log import DebugLog

from . import ir_http

_debug = DebugLog(__name__)


class Base(models.AbstractModel):
    _inherit = "base"

    def get_base_url(self):
        if not self:
            return super().get_base_url()
        self.check_singleton()

        if self._name == "website":
            return self.domain or super().get_base_url()
        if "website_id" in self and self.sudo().website_id.domain:
            _debug.logic("base_url", by="record_website", model=self._name)
            return self.sudo().website_id.domain
        if "company_id" in self and self.company_id.website_id.domain:
            _debug.logic("base_url", by="company_website", model=self._name)
            return self.company_id.website_id.domain
        return super().get_base_url()

    def get_website_meta(self):
        return {}

    def _get_base_lang(self):
        website = ir_http.get_request_website()
        if website:
            return website.default_lang_id.code
        return super()._get_base_lang()
