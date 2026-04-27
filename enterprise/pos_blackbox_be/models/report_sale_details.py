# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        data = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )
        sessions = []
        configs = []
        if config_ids:
            configs = self.env['pos.config'].search([('id', 'in', config_ids)])
            if session_ids:
                sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            else:
                sessions = self.env['pos.session'].search(
                    [('config_id', 'in', configs.ids), ('start_at', '>=', date_start), ('stop_at', '<=', date_stop)])
        else:
            sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            for session in sessions:
                configs.append(session.config_id)

        totalPaymentsAmount = 0
        for session in sessions:
            totalPaymentsAmount += session.total_payments_amount

        if len(sessions) == 1:
            session = sessions[0]
            if session.config_id.certified_blackbox_identifier:
                data = self._set_default_belgian_taxes_if_empty(data, "taxes", session.company_id)
                data = self._set_default_belgian_taxes_if_empty(data, "refund_taxes", session.company_id)
                report_update = {
                    "isBelgium": bool(session.config_id.certified_blackbox_identifier),
                    "cashier_name": session.user_id.name,
                    "insz_or_bis_number": session.user_id.insz_or_bis_number,
                    "NS_number": len(
                        self.env["pos.order"].search(
                            [("session_id", "=", session.id), ("amount_total", ">=", 0)]
                        )
                    ),
                    "NR_number": len(
                        self.env["pos.order"].search(
                            [("session_id", "=", session.id), ("amount_total", "<", 0)]
                        )
                    ),
                    "PS_number": session.pro_forma_sales_number,
                    "PS_amount": session.pro_forma_sales_amount,
                    "PR_number": session.pro_forma_refund_number,
                    "PR_amount": session.pro_forma_refund_amount,
                    "Positive_discount_number": len(
                        self.env["pos.order"]
                        .search(
                            [("session_id", "=", session.id), ("amount_total", ">=", 0)]
                        )
                        .filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0))
                    ),
                    "Negative_discount_number": len(
                        self.env["pos.order"]
                        .search(
                            [("session_id", "=", session.id), ("amount_total", "<", 0)]
                        )
                        .filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0))
                    ),
                    "Positive_discount_amount": session.get_total_discount_positive_negative(
                        True
                    ),
                    "Negative_discount_amount": session.get_total_discount_positive_negative(
                        False
                    ),
                    "Correction_number": session.correction_number,
                    "Correction_amount": session.correction_amount,
                    "CashBoxStartAmount": session.cash_register_balance_start,
                    "CashBoxEndAmount": session.cash_register_balance_end_real,
                    "cashRegisterID": session.config_id.name,
                    "CompanyVAT": session.company_id.vat,
                    "fdmID": session.config_id.certified_blackbox_identifier,
                    "CashBoxOpening": session.cash_box_opening_number,
                }
                data.update(report_update)
        data["total_paid"] = totalPaymentsAmount
        return data

    def _get_product_total_amount(self, line):
        return line.price_subtotal_incl

    def _get_total_and_qty_per_category(self, categories):
        res_cat, res_total = super()._get_total_and_qty_per_category(categories)
        if self.env.context.get('config_id') and self.env['pos.config'].browse(self.env.context.get('config_id')).certified_blackbox_identifier:
            for cat in res_cat:
                total_cat = 0
                for product in cat['products']:
                    total_cat += product['total_paid']
                cat['total'] = total_cat
            unique_products = list({tuple(sorted(product.items())): product for category in categories for product in category['products']}.values())
            res_total['total'] = sum(product['total_paid'] for product in unique_products)
        return res_cat, res_total

    def _set_default_belgian_taxes_if_empty(self, data, taxes_name, company):
        for tax in data[taxes_name]:
            tax_used = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('name', '=', tax['name']),
            ])
            tax['identification_letter'] = tax_used.tax_group_id.pos_receipt_label

        letter_set = ['A', 'B', 'C', 'D']
        for tax in data[taxes_name]:
            if tax['identification_letter'] in letter_set:
                letter_set.remove(tax['identification_letter'])

        for letter in letter_set:
            if letter == 'A':
                data[taxes_name].append({'name': '21%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
            if letter == 'B':
                data[taxes_name].append({'name': '12%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
            if letter == 'C':
                data[taxes_name].append({'name': '6%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
            if letter == 'D':
                data[taxes_name].append({'name': '0%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
        data[taxes_name] = sorted(data[taxes_name], key=lambda d: d['identification_letter'] or '', reverse=True)

        return data
