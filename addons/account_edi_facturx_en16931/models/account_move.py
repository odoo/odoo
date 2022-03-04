# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # TODO: remove in 15
    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is to prepare values in order to export an invoice through the EDI system.
        This includes the computation of the tax details for each invoice line that could be very difficult to
        handle regarding the computation of the base amount.
        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        res = {
            'record': self,
            'balance_multiplicator': -1 if self.is_inbound() else 1,
            'invoice_line_vals_list': [],
        }

        # Invoice lines details.
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda line: not line.display_type), start=1):
            line_vals = line._prepare_edi_vals_to_export()
            line_vals['index'] = index
            res['invoice_line_vals_list'].append(line_vals)

        # Totals.
        res.update({
            'total_price_subtotal_before_discount': sum(
                x['price_subtotal_before_discount'] for x in res['invoice_line_vals_list']),
            'total_price_discount': sum(x['price_discount'] for x in res['invoice_line_vals_list']),
        })
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # TODO: remove in 15
    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is the same as '_prepare_edi_vals_to_export' but for a single invoice line.
        This includes the computation of the tax details for each invoice line or the management of the discount.
        Indeed, in some EDI, we need to provide extra values depending the discount such as:
        - the discount as an amount instead of a percentage.
        - the price_unit but after subtraction of the discount.
        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        if self.discount == 100.0:
            gross_price_subtotal = self.currency_id.round(self.price_unit * self.quantity)
        else:
            gross_price_subtotal = self.currency_id.round(self.price_subtotal / (1 - self.discount / 100.0))

        res = {
            'line': self,
            'price_unit_after_discount': self.currency_id.round(self.price_unit * (1 - (self.discount / 100.0))),
            'price_subtotal_before_discount': gross_price_subtotal,
            'price_subtotal_unit': self.currency_id.round(
                self.price_subtotal / self.quantity) if self.quantity else 0.0,
            'price_total_unit': self.currency_id.round(self.price_total / self.quantity) if self.quantity else 0.0,
            'price_discount': gross_price_subtotal - self.price_subtotal,
            'gross_price_total_unit': self.currency_id.round(
                gross_price_subtotal / self.quantity) if self.quantity else 0.0,
        }
        return res