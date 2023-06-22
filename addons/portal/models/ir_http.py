# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.tools import consteq


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['portal']

    @classmethod
    def _get_frontend_langs(cls):
        if request and request.is_frontend:
            return [lang[0] for lang in filter(lambda l: l[3], request.env['res.lang'].get_available())]
        return super()._get_frontend_langs()

    def _check_access(self, model, record, field, access_token):
        if isinstance(record, self.env.registry['portal.mixin']):
            record_sudo = record.sudo()
            attachment = self.sudo().env['ir.attachment'].search([('res_model', '=', model), ('res_id', '=', record.id), ('res_field', '=', field)])
            if access_token and consteq(attachment.access_token or '', access_token):
                return record_sudo
        return super()._check_access(model, record, field, access_token)
