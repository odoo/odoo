# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModel(models.Model):
    _inherit = 'ir.model'

    def unlink(self):
        # Delete followers for models that will be unlinked.
        query = "DELETE FROM mail_followers WHERE res_model IN %s"
        self.env.cr.execute(query, [tuple(self.mapped('model'))])
        return super(IrModel, self).unlink()
