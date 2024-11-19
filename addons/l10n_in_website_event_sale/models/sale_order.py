from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        values = super(SaleOrder, self)._prepare_invoice()
        if not self.website_id:
            return values

        for line in self.order_line:
            if line.event_id.l10n_in_state_id and\
                (line.event_id.l10n_in_pos_treatment == 'always' or\
                (line.event_id.l10n_in_pos_treatment == 'for_unregistered'\
                and self.l10n_in_gst_treatment in ['consumer', 'unregistered'])):
                values['l10n_in_state_id'] = line.event_id.l10n_in_state_id.id
        return values
