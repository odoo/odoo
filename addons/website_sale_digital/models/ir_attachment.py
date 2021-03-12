# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import AccessError


class Attachment(models.Model):

    _inherit = ['ir.attachment']

    product_downloadable = fields.Boolean("Downloadable from product portal", default=False)

    @api.model
    def check(self, mode, values=None):
        super().check(mode, values=values)
        if mode == 'read' and self and not self.env.user.has_group('base.group_user'):
            self._cr.execute('SELECT 1 FROM ir_attachment WHERE product_downloadable AND id IN %s', [tuple(self.ids)])
            if self._cr.rowcount:
                raise AccessError(_("Sorry, you are not allowed to access this document."))

        super(Attachment, self).check(mode, values)
