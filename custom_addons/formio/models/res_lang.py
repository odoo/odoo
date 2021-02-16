# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, fields, models


class ResLang(models.Model):
    _inherit = 'res.lang'

    formio_ietf_code = fields.Char(compute='_compute_formio_ietf_code', string='IETF Code')

    def _compute_formio_ietf_code(self):
        for lang in self:
            lang.formio_ietf_code = self._formio_ietf_code(lang.code)

    @api.model
    def _formio_ietf_code(self, code):
        return code.replace('_', '-')
