# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_latam_document_type_id = fields.Many2one(
        related='move_id.l10n_latam_document_type_id', auto_join=True, store=True, index=True)
    l10n_latam_price_unit = fields.Monetary(compute='compute_l10n_latam_prices_and_taxes')
    l10n_latam_price_subtotal = fields.Monetary(compute='compute_l10n_latam_prices_and_taxes')
    l10n_latam_price_net = fields.Monetary(compute='compute_l10n_latam_prices_and_taxes')
    l10n_latam_tax_ids = fields.One2many(compute="compute_l10n_latam_prices_and_taxes", comodel_name='account.tax')

    @api.depends('price_unit', 'price_subtotal', 'move_id.l10n_latam_document_type_id')
    def compute_l10n_latam_prices_and_taxes(self):
        for line in self:
            invoice = line.move_id
            included_taxes = \
                invoice.l10n_latam_document_type_id and invoice.l10n_latam_document_type_id._filter_taxes_included(
                    line.tax_ids)
            if not included_taxes:
                price_unit = line.tax_ids.with_context(round=False).compute_all(
                    line.price_unit, invoice.currency_id, 1.0, line.product_id, invoice.partner_id)
                l10n_latam_price_unit = price_unit['total_excluded']
                l10n_latam_price_subtotal = line.price_subtotal
                not_included_taxes = line.tax_ids
                l10n_latam_price_net = l10n_latam_price_unit * (1 - (line.discount or 0.0) / 100.0)
            else:
                not_included_taxes = line.tax_ids - included_taxes
                l10n_latam_price_unit = included_taxes.compute_all(
                    line.price_unit, invoice.currency_id, 1.0, line.product_id, invoice.partner_id)['total_included']
                l10n_latam_price_net = l10n_latam_price_unit * (1 - (line.discount or 0.0) / 100.0)
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                l10n_latam_price_subtotal = included_taxes.compute_all(
                    price, invoice.currency_id, line.quantity, line.product_id,
                    invoice.partner_id)['total_included']

            line.l10n_latam_price_subtotal = l10n_latam_price_subtotal
            line.l10n_latam_price_unit = l10n_latam_price_unit
            line.l10n_latam_price_net = l10n_latam_price_net
            line.l10n_latam_tax_ids = not_included_taxes
