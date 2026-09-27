from odoo import api, models


class IrAccess(models.Model):
    _inherit = 'ir.access'

    @api.model
    def _eval_context(self):
        res = super()._eval_context()
        res['website'] = self.env.website
        return res

    def _get_access_context(self):
        yield from super()._get_access_context()
        yield self.env.context.get('website_id')
