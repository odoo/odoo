# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def can_edit_vat(self):
        ''' `vat` is a commercial field, synced between the parent (commercial
        entity) and the children. Only the commercial entity should be able to
        edit it (as in backend). '''
        return not self.parent_id

    @api.model
    def _get_current_persona(self):
        if partner := self.env["res.partner"]._get_partner_from_context():
            return (partner, self.env["mail.guest"])
        return super()._get_current_persona()

    def _get_partner_from_context(self):
        return self.env.context.get("portal_partner")
