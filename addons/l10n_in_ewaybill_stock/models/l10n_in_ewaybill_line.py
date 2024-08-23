# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EwaybillStockLine(models.Model):
    _name = "l10n.in.ewaybill.line"
    _description = "Ewaybill lines for stock movement"

    stock_move_id = fields.Many2one("stock.move")

    ewaybill_id = fields.Many2one(
        comodel_name='l10n.in.ewaybill',
        required=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product', related="stock_move_id.product_id")

    quantity = fields.Float(
        'Quantity Done', digits='Product Unit of Measure', related="stock_move_id.quantity_done")

    product_uom = fields.Many2one(
        'uom.uom', "UoM", related="stock_move_id.product_uom")

    company_id = fields.Many2one(
        related='stock_move_id.company_id')

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id')

    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        readonly=False)

    igst_rate = fields.Float("IGST Rate", compute="_compute_rate_amount")
    igst_amount = fields.Float("IGST Amount", compute="_compute_rate_amount")
    cgst_rate = fields.Float("CGST Rate", compute="_compute_rate_amount")
    cgst_amount = fields.Float("CGST Amount", compute="_compute_rate_amount")
    sgst_rate = fields.Float("SGST Rate", compute="_compute_rate_amount")
    sgst_amount = fields.Float("SGST Amount", compute="_compute_rate_amount")
    cess_rate = fields.Float("CESS Rate", compute="_compute_rate_amount")
    cess_amount = fields.Float("CESS Amount", compute="_compute_rate_amount")
    cess_non_advol_amount = fields.Float("CESS NON ADVOL Amount", compute="_compute_rate_amount")
    other_amount = fields.Float("Other Amount", compute="_compute_rate_amount")

    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        digits='Product Price', readonly=False,
        store=True)

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount', readonly=True,
        store=True)
    price_tax = fields.Float(
        string="Total Tax",
        compute='_compute_amount', readonly=True,
        store=True)
    price_total = fields.Monetary(
        string="Total",
        compute='_compute_amount', readonly=True,
        store=True)

    @api.depends('product_id', 'product_uom', 'quantity')
    def _compute_price_unit(self):
        for line in self:
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
            else:
                line.price_unit = line.product_id._get_tax_included_unit_price(
                    line.ewaybill_id.company_id,
                    line.ewaybill_id.currency_id,
                    line.ewaybill_id.date or fields.Datetime.now(),
                    'sale',
                    product_uom=line.product_uom,
                    product_currency=line.currency_id
                )

    def _convert_to_tax_base_line_dict(self, **kwargs):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.price_unit,
            quantity=self.quantity,
            price_subtotal=self.price_subtotal,
            **kwargs,
        )

    @api.depends('quantity', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([
                line._convert_to_tax_base_line_dict()
            ])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    @api.depends('price_unit', 'tax_ids')
    def _compute_rate_amount(self):
        for record in self:
            record.igst_rate = 0.0
            record.igst_amount = 0.0
            record.cgst_rate = 0.0
            record.cgst_amount = 0.0
            record.sgst_rate = 0.0
            record.sgst_amount = 0.0
            record.cess_rate = 0.0
            record.cess_amount = 0.0
            record.cess_non_advol_amount = 0.0
            record.other_amount = 0.0

            taxes = record.tax_ids.compute_all(price_unit=record.price_unit, quantity=record.quantity)

            for tax in taxes['taxes']:
                if isinstance(tax['id'], int):
                    tax_id = self.env['account.tax'].browse(tax['id'])
                else:
                    tax_id = self.env['account.tax'].browse(tax['id'].origin)

                if self.env.ref("l10n_in.tax_tag_igst").id in tax['tag_ids']:
                    record.igst_rate += tax_id.amount
                    record.igst_amount += tax['amount']

                elif self.env.ref("l10n_in.tax_tag_cgst").id in tax['tag_ids']:
                    record.cgst_rate += tax_id.amount
                    record.cgst_amount += tax['amount']

                elif self.env.ref("l10n_in.tax_tag_sgst").id in tax['tag_ids']:
                    record.sgst_rate += tax_id.amount
                    record.sgst_amount += tax['amount']

                elif self.env.ref("l10n_in.tax_tag_cess").id in tax['tag_ids']:
                    if tax_id.amount_type != "percent":
                        record.cess_non_advol_amount += tax['amount']
                    else:
                        record.cess_rate = tax_id.amount
                        record.cess_amount += tax['amount']
                else:
                    record.other_amount += tax['amount']
