# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import models


# This is a nasty hack, targeted for V11 only
class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    def unlink(self):
        # Prevent the deletion of some `shared` fields... -_-
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
                (rec.model == 'res.company' and rec.name in social)
                or (rec.model == 'res.config.settings'
                    and rec.name == 'auth_signup_uninvited')
            )
        )
        return super(IrModelFields, self).unlink()
