# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    intercompany_warehouse_id = fields.Many2one(
        related='company_id.intercompany_warehouse_id',
        string="Warehouse For Purchase Orders",
        readonly=False,
        domain=lambda self: [('company_id', '=', self.env.company.id)],
    )
    intercompany_receipt_type_id = fields.Many2one(
        related='company_id.intercompany_receipt_type_id',
        readonly=False,
        domain=lambda self: [('warehouse_id.company_id', '=', self.env.company.id), ('code', '=', 'incoming')],
    )
    intercompany_sync_delivery_receipt = fields.Boolean(related='company_id.intercompany_sync_delivery_receipt', readonly=False)
