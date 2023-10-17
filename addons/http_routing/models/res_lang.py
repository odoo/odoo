import functools
from odoo import api, models
from odoo.tools import get_lang


class Lang(models.Model):
    _inherit = "res.lang"

    def _routing_fields(self):
        return {'id', 'name', 'code', 'url_code'}

    def _routing_data(self):
        self = self.with_context(active_test=True)
        return self.search_read([], list(self._routing_fields()), load=False)

    def _routing_default_lang(self):
        self = self.with_context(active_test=True)
        lang_code = self.env['ir.default']._get('res.partner', 'lang')
        lang = self._lang_get(lang_code) if lang_code else get_lang(self.env)
        return lang.read(list(self._routing_fields()))[0]

    @api.model_create_multi
    def create(self, vals_list):
        super().create(vals_list)
        self.env.cr.postcommit.add(
            functools.partial(self.env.registry.clear_cache, 'routing'))

    def write(self, vals):
        super().write(vals)
        if not self._routing_fields().isdisjoint(vals):
            self.env.cr.postcommit.add(
                functools.partial(self.env.registry.clear_cache, 'routing'))

    def unlink(self):
        super().unlink()
        self.env.cr.postcommit.add(
            functools.partial(self.env.registry.clear_cache, 'routing'))
