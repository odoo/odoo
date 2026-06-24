# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.tools import SQL

from odoo.addons.account.report.account_invoice_report import compute_sql, related_sql


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    l10n_ar_state_id = fields.Many2one('res.country.state', 'Delivery Province', **compute_sql('l10n_ar_state_id', lambda self, table: self._compute_sql_l10n_ar_state_id(table)))
    date = fields.Date(string="Accounting Date", **related_sql('move_id.date'))

    def _compute_sql_l10n_ar_state_id(self, table):
        contact_partner_alias = table._make_alias('contact_partner', self.env['res.partner'])
        table._query.add_join('LEFT JOIN', contact_partner_alias, 'res_partner', SQL(
            "%s = COALESCE(%s, %s)",
            contact_partner_alias.id, table.move_id.partner_shipping_id, table.move_id.partner_id,
        ))
        return contact_partner_alias.state_id
