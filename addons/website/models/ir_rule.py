# coding: utf-8
from odoo import api, models


class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _eval_context(self):
        res = super(IrRule, self)._eval_context()
        res['website_id'] = self._context.get('website_id')
        return res
