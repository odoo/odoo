# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import AccessError


class Attachment(models.Model):

    _inherit = ['ir.attachment']

    product_downloadable = fields.Boolean("Downloadable from product portal", default=False)

    @api.model
    def check(self, mode, values=None):
        if self:
            self._cr.execute('SELECT product_downloadable FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
            for product_downloadable, in self._cr.fetchall():
                if product_downloadable and not (self.env.user._is_admin() or self.env.user.has_group('base.group_user')):
                    raise AccessError(_("Sorry, you are not allowed to access this document."))

        super(Attachment, self).check(mode, values)