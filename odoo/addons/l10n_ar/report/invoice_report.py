# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    l10n_ar_state_id = fields.Many2one('res.country.state', 'Delivery Province', readonly=True)
    date = fields.Date(readonly=True, string="Accounting Date")

    _depends = {
        'account.move': ['partner_shipping_id', 'date'],
        'res.partner': ['state_id'],
    }

    def _select(self):
        return super()._select() + ", contact_partner.state_id as l10n_ar_state_id, move.date"

    def _from(self):
        return super()._from() + " LEFT JOIN res_partner contact_partner ON contact_partner.id = COALESCE(move.partner_shipping_id, move.partner_id)"
