# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = ['res.partner']

    def _default_category(self):
        if self._context.get('unset_res_partner_category_id'):
            return False
        return super()._default_category()

    category_id = fields.Many2many(default=_default_category)
