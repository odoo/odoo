# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    l10n_ar_state_id = fields.Many2one('res.country.state', 'State', readonly=True)
    date = fields.Date(readonly=True, string="Accounting Date")

    _depends = {
        'account.move': ['partner_id', 'date'],
        'res.partner': ['state_id'],
    }

    def _select(self):
        """ If sale is installed we have the partner_shipping_id column, then use this field to get the state """
        if self.env['account.move']._fields.get('partner_shipping_id'):
            select = ", COALESCE( delivery_partner.state_id, contact_partner.state_id) as l10n_ar_state_id, move.date"
        else:
            select = ", contact_partner.state_id as l10n_ar_state_id, move.date"
        return super()._select() + select

    def _group_by(self):
        return super()._group_by() + ", l10n_ar_state_id, move.date"

    def _from(self):
        res = super()._from() + " LEFT JOIN res_partner contact_partner ON contact_partner.id = move.partner_id"
        if self.env['account.move']._fields.get('partner_shipping_id'):
            res += " LEFT JOIN res_partner delivery_partner ON delivery_partner.id = move.partner_shipping_id"
        return res
