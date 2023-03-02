from odoo import models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_l10n_de_addresses(self):
        #OVERRIDE to sync the report formate same as Sales report
        for record in self:
            record.l10n_de_addresses = data = []
            if not record.partner_shipping_id or record.partner_shipping_id == record.partner_id:
                data.append((_("Invoicing and Shipping Address:"), record.partner_id))
            else:
                data.append((_("Shipping Address:"), record.partner_shipping_id))
                data.append((_("Invoicing Address:"), record.partner_id))
                