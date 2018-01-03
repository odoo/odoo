# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, models


# This is a nasty hack, targeted for V11 only
class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    @api.multi
    def unlink(self):
        # Prevent the deletion of social_* fields defined in res.company if
        # the other module is installed
        social = (
            'social_facebook',
            'social_github',
            'social_googleplus',
            'social_linkedin',
            'social_twitter',
            'social_youtube',
        )

        self = self.filtered(
            lambda rec: not (
                rec.model == 'res.company' and
                rec.name in social
            )
        )
        return super(IrModelFields, self).unlink()
