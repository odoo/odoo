# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import utm, mass_mailing


class UtmTestSourceMixin(models.Model, utm.UtmSourceMixin):
    """ Test utm.source.mixin """
    _description = "UTM Source Mixin Test Model"
    _order = "id DESC"
    _rec_name = "title"

    name = fields.Char(inherited=True)
    title = fields.Char()


class UtmTestSourceMixinOther(models.Model, mass_mailing.MailThread, utm.UtmSourceMixin):
    """ Test utm.source.mixin, similar to the other one, allowing also to test
    cross model uniqueness check """
    _description = "UTM Source Mixin Test Model (another)"
    _order = "id DESC"
    _rec_name = "title"

    name = fields.Char(inherited=True)
    title = fields.Char()
