from odoo import api, models


class PdpFlow10XMLBuilder(models.AbstractModel):
    _inherit = 'pdp.flow.10.xml.builder'

    @api.model
    def _invoice_add_allowance_charges(self, invoice, move, seller, buyer):
        # Todo IGBE - not sure yet I need this, keeping it for track
        return super()._invoice_add_allowance_charges(invoice, move, seller, buyer)
