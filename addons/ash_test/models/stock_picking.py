from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tenant_id = fields.Char('Tenant ID')
    site_code = fields.Char('Site Code')

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        if res.move_ids:
            for move in res.move_ids:
                product = move.product_id.product_tmpl_id
                product.write({
                    'tenant_id': res.tenant_id,
                    'site_code': res.site_code,
                })
        return res

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        for picking in self:
            if picking.move_ids:
                for move in picking.move_ids:
                    product = move.product_id.product_tmpl_id
                    product.write({
                        'tenant_id': picking.tenant_id,
                        'site_code': picking.site_code,
                    })
        return res
