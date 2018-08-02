# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

class MailMessageSubtype(models.Model):
    _inherit = 'mail.message.subtype'

    def _get_department_subtype(self):
        return self.search([
            ['res_model', '=', 'hr.department'],
            ['parent_id', '=', self.id],
        ])

    def _update_department_subtype(self):
        subtype = self._get_department_subtype()
        if subtype:
            super(MailMessageSubtype, subtype).write({
                'name': self.name,
                'default': self.default,
            })
        else:
            subtype = super(MailMessageSubtype, self).create({
                'name': self.name,
                'res_model': 'hr.department',
                'default': self.default or False,
                'parent_id': self.id,
                'relation_field': 'department_id',
            })
        return subtype

    @api.model
    def create(self, vals):
        result = super(MailMessageSubtype, self).create(vals)
        if result.res_model in ['hr.leave', 'hr.leave.allocation']:
            result._update_department_subtype()
        return result

    @api.multi
    def write(self, vals):
        result = super(MailMessageSubtype, self).write(vals)
        if self.res_model in ['hr.leave', 'hr.leave.allocation']:
            self._update_department_subtype()
        return result
