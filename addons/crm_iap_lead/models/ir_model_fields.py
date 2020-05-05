# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import models


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    def unlink(self):
        # Nasty hack to prevent the deletion of shared field reveal_id
        self = self.filtered(
            lambda rec: not (
                rec.model == 'crm.lead'
                and rec.name == 'reveal_id'
            )
        )
        return super(IrModelFields, self).unlink()
