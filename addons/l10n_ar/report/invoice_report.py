# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    l10n_ar_state_id = fields.Many2one('res.country.state', 'Delivery Province', readonly=True)
    date = fields.Date(readonly=True, string="Accounting Date")

    def _select_list(self, table):
        contact_partner_alias = table._make_alias('contact_partner', self.env['res.partner'])
        table._query.add_join('LEFT JOIN', contact_partner_alias, 'res_partner', SQL(
            "%s = COALESCE(%s, %s)",
            contact_partner_alias.id, table.move_id.partner_shipping_id, table.move_id.partner_id,
        ))
        return super()._select_list(table) + [
            SQL("%s AS l10n_ar_state_id", contact_partner_alias.state_id),
            table.move_id.date,
        ]
