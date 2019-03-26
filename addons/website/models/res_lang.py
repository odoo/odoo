# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Lang(models.Model):
    _inherit = "res.lang"

    @api.multi
    def write(self, vals):
        if 'active' in vals and not vals['active']:
            if self.env['website'].search([('language_ids', 'in', self._ids)]):
                raise UserError(_("Cannot deactivate a language that is currently used on a website."))
        return super(Lang, self).write(vals)

    def _get_request_lang(self):
        for lang in self:
            lang.request_lang = lang.website_lang_code or lang.iso_code

    website_lang_code = fields.Char(string='Website Lang code', help='This field is use for translation on website')
