from odoo import api, models


class PortalShare(models.TransientModel):
    _inherit = 'portal.share'

    @api.model
    def default_get(self, fields):
        # EXTENDS portal
        # The link handed out presents the order to whoever opens it, and the customer's page never
        # issues it: issue it first, as the internal user sharing it, as opening the send
        # wizard does. Not in `sale.order._get_share_url`, which core also calls for a portal
        # user following a `/mail/view` link.
        if self.env.context.get('active_model') == 'sale.order' and (order_id := self.env.context.get('active_id')):
            self.env['sale.order'].browse(order_id)._l10n_pt_issue()
        return super().default_get(fields)
