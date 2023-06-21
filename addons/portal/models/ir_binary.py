# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import consteq


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record_check_access(self, record, access_token):
        if isinstance(record, self.env.registry['portal.mixin']):
            record_sudo = record.sudo()
            if access_token and consteq(record_sudo.with_context(prefetch_fields=False).access_token, access_token):
                return record_sudo
        return super()._find_record_check_access(record, access_token)
