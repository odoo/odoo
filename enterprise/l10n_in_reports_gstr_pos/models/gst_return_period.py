# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class L10nInReportAccount(models.Model):
    _inherit = "l10n_in.gst.return.period"

    # ===============================
    # GSTR-1
    # ===============================

    def _get_gstr1_hsn_json(self, journal_items, tax_details_by_move):
        """
            We need to show all sold products by product HSN code and in the journal items for POS, it is grouped by tax and sign
            So we check which pos order lines match with which grouped journal items so get a ratio by HSN code + tax rate.
            POS Session Journal Items:
                          Label                       | debit     | credit | tag ids |
            ==========================================|===========|========|=========|
            Sales with SGST Sale 2.5%, CGST Sale 2.5% | 10,200.00 | 0.0    |         |
            SGST sale 2.5%                            |    255.00 | 0.0    | +SGST   |
            CGST sale 2.5%                            |    255.00 | 0.0    | +CGST   |
            POS Order Lines:
            Product name | Product HSN | tax_ids | amount    |
            =============|=============|=========|===========|
            Mobile       | 8517        | GST 5%  | 10,000.00 |
            Mobile cover | 3919        | GST 5%  |    200.00 |
            in this case ratio for first line is 0.98(~) and for second line 0.0196(~)
            In this hsn json as below
            [{
                "hsn_sc": "8517",
                "uqc": "UNT",
                "rt": 5.0,
                "qty": 1.0,
                "txval": 10000.0,
                "iamt": 0.0,
                "samt": 250.0, (255.00 * (10000.0/10200.00))
                "camt": 250.0, (255.00 * (10000.0/10200.00))
                "csamt": 0.0
            },
            {
                "hsn_sc": "3919",
                "uqc": "UNT",
                "rt": 5.0,
                "qty": 1.0,
                "txval": 200.0,
                "iamt": 0.0,
                "samt": 5.0, (255.00 * (200.0/10200.00))
                "camt": 5.0, (255.00 * (200.0/10200.00))
                "csamt": 0.0
            }]
        """
        def _set_details_pos_lines(pos_order_lines):
            # Pre-warming cache so that accessing product.product fields is faster per iteration by
            # reducing retrieval time for the fields 'type' and 'l10n_in_hsn_code'
            products = self.env['product.product'].browse(pos_order_lines.product_id.ids)
            products.fetch(['type'])
            uoms = self.env['uom.uom'].search_fetch([], ['l10n_in_code'], order=None)

            details_pos_lines = {}
            for pos_order_line in pos_order_lines:
                move_id = pos_order_line.order_id.session_move_id.id
                income_account = pos_order_line.product_id.with_company(pos_order_line.company_id)._get_product_accounts()["income"] or pos_order_line.order_id.config_id.journal_id.default_account_id
                if pos_order_line.order_id.fiscal_position_id:
                    income_account = pos_order_line.order_id.fiscal_position_id.map_account(income_account)
                details_pos_lines.setdefault(move_id, {})
                if products.browse(pos_order_line.product_id.id).type == 'service':
                    uom_code = "NA"
                    product_qty = 0
                else:
                    uom_code = (
                        uoms.browse(pos_order_line.product_uom_id.id).l10n_in_code and
                        uoms.browse(pos_order_line.product_uom_id.id).l10n_in_code.split("-")[0] or "OTH"
                    )
                    product_qty = pos_order_line.qty
                details_pos_lines[move_id][pos_order_line.id] = {
                    "account_id": income_account.id,
                    "price_subtotal": pos_order_line.price_subtotal,
                    "tax_ids": pos_order_line.tax_ids_after_fiscal_position.flatten_taxes_hierarchy().ids,
                    "qty": product_qty,
                    "product_hsn_code": self.env["account.edi.format"]._l10n_in_edi_extract_digits(pos_order_line.l10n_in_hsn_code),
                    "currency_rate": pos_order_line.order_id.currency_rate,
                    "product_uom_code": uom_code
                }
            return details_pos_lines

        def _is_pos_order_line_matched_account_move_line(account_move_line, details_pos_line):
            return details_pos_line['account_id'] == account_move_line.account_id.id \
                and ((account_move_line.credit > 0.00 and details_pos_line['price_subtotal'] > 0.00) \
                or (account_move_line.debit > 0.00 and details_pos_line['price_subtotal'] < 0.00)) \
                and sorted(details_pos_line['tax_ids']) == sorted(account_move_line.tax_ids.ids)

        pos_journal_items = journal_items.filtered(lambda l: l.move_id.pos_session_ids and l.move_id.move_type == "entry")
        hsn_json = super()._get_gstr1_hsn_json(journal_items - pos_journal_items, tax_details_by_move)
        # Extract all POS orders related to the POS journal items
        all_pos_orders = pos_journal_items.move_id.pos_session_ids.order_ids
        # Split orders into invoiced and non-invoiced
        non_invoiced_orders = all_pos_orders.filtered(lambda o: not o.is_invoiced)
        invoiced_orders = all_pos_orders - non_invoiced_orders
        # Include the original POS orders that got reversed after session close
        reversal_data = self.env['account.move'].search_read(
            domain=[('reversed_pos_order_id', 'in', invoiced_orders.ids)],
            fields=['reversed_pos_order_id'],
        )
        reversed_order_ids = [rec['reversed_pos_order_id'][0] for rec in reversal_data]
        reversed_orders = self.env['pos.order'].browse(reversed_order_ids)
        pos_orders = non_invoiced_orders | reversed_orders
        pos_order_lines = self.env['pos.order.line'].browse(pos_orders.lines.ids)
        pos_order_lines.fetch(['product_id', 'product_uom_id'])
        details_pos_lines_by_move = _set_details_pos_lines(pos_order_lines)
        hsn_new_schema_apply_date = self._get_hsn_new_schema_apply_date()
        hsn_section = 'data' if self.start_date < hsn_new_schema_apply_date else 'hsn_b2c'
        hsn_json.setdefault(hsn_section, {})
        for move_id in pos_journal_items.mapped("move_id"):
            tax_details = tax_details_by_move.get(move_id)
            details_pos_lines = details_pos_lines_by_move.get(move_id.id)
            if not details_pos_lines:
                continue
            for line, line_tax_details in tax_details.items():
                tax_rate = line_tax_details['gst_tax_rate']
                if tax_rate.is_integer():
                    tax_rate = int(tax_rate)
                pos_matched_lines = list(filter(lambda pol: _is_pos_order_line_matched_account_move_line(line, details_pos_lines[pol]), details_pos_lines))
                remaining_values = {
                    "txval": line_tax_details.get('base_amount', 0.00) * -1,
                    "iamt": line_tax_details.get('igst', 0.00) * -1,
                    "samt": line_tax_details.get('sgst', 0.00) * -1,
                    "camt": line_tax_details.get('cgst', 0.00) * -1,
                    "csamt": line_tax_details.get('cess', 0.00) * -1,
                }
                for index, pos_order_line_id in enumerate(pos_matched_lines, start=1):
                    details_pos_line = details_pos_lines[pos_order_line_id]
                    price_subtotal = details_pos_line['price_subtotal'] * details_pos_line['currency_rate']
                    pos_ratio = abs(price_subtotal / abs(line.balance))
                    product_uom_code = details_pos_line['product_uom_code']
                    product_hsn_code = details_pos_line['product_hsn_code']
                    group_key = "%s-%s-%s" % (tax_rate, product_hsn_code, product_uom_code)
                    hsn_json[hsn_section].setdefault(group_key, {
                        "hsn_sc": product_hsn_code,
                        "uqc": product_uom_code,
                        "rt": tax_rate,
                        "qty": 0.00, "txval": 0.00, "iamt": 0.00, "samt": 0.00, "camt": 0.00, "csamt": 0.00})
                    hsn_data = hsn_json[hsn_section][group_key]
                    hsn_data['qty'] += details_pos_line['qty']
                    # check is last in loop
                    if index == len(pos_matched_lines):
                        hsn_data['txval'] += remaining_values['txval']
                        hsn_data['iamt'] += remaining_values['iamt']
                        hsn_data['samt'] += remaining_values['samt']
                        hsn_data['camt'] += remaining_values['camt']
                        hsn_data['csamt'] += remaining_values['csamt']
                    else:
                        hsn_data['txval'] += line_tax_details.get('base_amount', 0.00) * pos_ratio * -1
                        hsn_data['iamt'] += line_tax_details.get('igst', 0.00) * pos_ratio * -1
                        hsn_data['samt'] += line_tax_details.get('cgst', 0.00) * pos_ratio * -1
                        hsn_data['camt'] += line_tax_details.get('sgst', 0.00) * pos_ratio * -1
                        hsn_data['csamt'] += line_tax_details.get('cess', 0.00) * pos_ratio * -1

                        remaining_values['txval'] -= line_tax_details.get('base_amount', 0.00) * pos_ratio * -1
                        remaining_values['iamt'] -= line_tax_details.get('igst', 0.00) * pos_ratio * -1
                        remaining_values['samt'] -= line_tax_details.get('cgst', 0.00) * pos_ratio * -1
                        remaining_values['camt'] -= line_tax_details.get('sgst', 0.00) * pos_ratio * -1
                        remaining_values['csamt'] -= line_tax_details.get('cess', 0.00) * pos_ratio * -1
        return hsn_json

    def _get_section_domain(self, section_code):
        domain = super()._get_section_domain(section_code)
        if section_code == "b2cs":
            domain.remove(("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]))
            domain.remove(("move_id.l10n_in_gst_treatment", "in", ("unregistered", "consumer")))
            domain += ["|",
            "&", ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                ("move_id.l10n_in_gst_treatment", "in", ("unregistered", "consumer")),
            "&", ("move_id.move_type", "=", "entry"),
            "|", ("move_id.pos_session_ids", "!=", False),
                ('move_id.reversed_pos_order_id', '!=', False),
            ]
        if section_code == "nil":
            domain.remove(("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]))
            domain += ["|", "&",
                ("move_id.move_type", "=", "entry"),
                ("move_id.pos_session_ids", "!=", False),
                ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
            ]
        if section_code == "hsn":
            domain.remove(("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]))
            domain += ["|", "&",
                ("move_id.move_type", "=", "entry"),
                "|", ("move_id.pos_session_ids", "!=", False),
                    ('move_id.reversed_pos_order_id', '!=', False),
                ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
            ]
        return domain
