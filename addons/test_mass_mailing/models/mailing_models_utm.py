# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class UtmTestSourceMixin(models.Model):
    """ Test utm.source.mixin """
    _name = 'utm.test.source.mixin'
    _description = "UTM Source Mixin Test Model"
    _order = "id DESC"
    _rec_name = "title"
    _inherit = [
        "utm.source.mixin",
    ]

    name = fields.Char(inherited=True)
    title = fields.Char()


class UtmTestSourceMixinOther(models.Model):
    """ Test utm.source.mixin, similar to the other one, allowing also to test
    cross model uniqueness check """
    _name = 'utm.test.source.mixin.other'
    _description = "UTM Source Mixin Test Model (another)"
    _order = "id DESC"
    _rec_name = "title"
    _inherit = [
        "mail.thread",
        "utm.source.mixin",
    ]

    name = fields.Char(inherited=True)
    title = fields.Char()
