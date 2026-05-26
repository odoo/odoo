import re
from collections import defaultdict
<<<<<<< 455b6ae293e68ae48a752ff0825cb8431dd2bc43
||||||| 4b29bdf7c3f57ff573b89a32c4b8229c5c6d0cbb
from datetime import datetime

import psycopg2.errors
=======
from datetime import date, datetime

import psycopg2.errors
>>>>>>> 5478122285e5c29700791dd4deab8f24e0dea376

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nInEwaybill(models.Model):

    _inherit = 'l10n.in.ewaybill'
    _check_company_auto = True

    state = fields.Selection(
        selection_add=[('challan', "Challan")],
        ondelete={
            'challan': 'cascade'
        }
    )
    type_description = fields.Char(string="Description")

    # Stock picking details
    picking_id = fields.Many2one('stock.picking', "Stock Transfer", copy=False)
    move_ids = fields.One2many(related='picking_id.move_ids')
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal Position",
        compute='_compute_fiscal_position',
        check_company=True,
        store=True,
        readonly=False
    )

    @api.depends('name', 'state')
    def _compute_display_name(self):
        challan = self.filtered(lambda ewb: ewb.state == 'challan')
        challan.display_name = _("Challan")
        super(L10nInEwaybill, self - challan)._compute_display_name()

    def _get_ewaybill_dependencies(self):
        return ['account_move_id', 'picking_id']

    def _get_ewaybill_company(self):
        self.ensure_one()
        if self.picking_id:
            return self.picking_id.company_id
        return super()._get_ewaybill_company()

    def _get_ewaybill_document_details(self):
        """
        Returns document details
        :return: {'document_number': document_number, 'document_date': document_date}
        :rtype: dict
        """
        self.ensure_one()
        if picking_id := self.picking_id:
            return {
                'document_number': picking_id.name,
                'document_date': picking_id.date_done
            }
        return super()._get_ewaybill_document_details()

    def _get_seller_buyer_details(self):
        self.ensure_one()
        if picking_id := self.picking_id:
            if self._is_incoming():
                seller_buyer_details = {
                    "seller_details": picking_id.partner_id,
                    "dispatch_details": picking_id.partner_id,
                    "buyer_details": picking_id.company_id.partner_id,
                    "ship_to_details": picking_id.picking_type_id.warehouse_id.partner_id,
                }
            else:
                seller_buyer_details = {
                    "seller_details": picking_id.company_id.partner_id,
                    "dispatch_details": picking_id.picking_type_id.warehouse_id.partner_id,
                    "buyer_details": picking_id._l10n_in_get_invoice_partner() or picking_id.partner_id,
                    "ship_to_details": picking_id.partner_id,
                }
            if (
                picking_id.picking_type_id.code == 'dropship' and
                (dest_partner := picking_id._get_l10n_in_dropship_dest_partner())
            ):
                seller_buyer_details.update({
                    "ship_to_details": dest_partner,
                    "dispatch_details": picking_id.partner_id
                })
            return seller_buyer_details
        return super()._get_seller_buyer_details()

    def _is_incoming(self):
        self.ensure_one()
        if self.picking_id:
            return self.picking_id.picking_type_id.code == 'incoming'
        return super()._is_incoming()

    @api.depends('partner_bill_from_id', 'partner_bill_to_id')
    def _compute_fiscal_position(self):
        for ewaybill in self:
            if ewaybill.picking_id and ewaybill.state == 'pending':
                ewaybill.fiscal_position_id = (
                    self.env['account.fiscal.position']._get_fiscal_position(
                        ewaybill._is_incoming()
                        and ewaybill.partner_bill_from_id
                        or ewaybill.partner_bill_to_id
                    )
                    or ewaybill.picking_id._l10n_in_get_fiscal_position()
                )

    def action_reset_to_pending(self):
        self.ensure_one()
        if self.picking_id:
            if self.state not in ('cancel', 'challan'):
                raise UserError(_(
                    "Only Delivery Challan and Cancelled E-waybill can be reset to pending."
                ))
            self.write({
                'name': False,
                'state': 'pending',
                'cancel_reason': False,
                'cancel_remarks': False,
            })
        else:
            return super().action_reset_to_pending()

    def action_set_to_challan(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_(
                "The challan can only be generated in the Pending state."
            ))
        self.write({
            'state': 'challan',
        })

    def action_print(self):
        self.ensure_one()
        if self.state == 'generated':
            return super().action_print()
        if self.state != 'challan':
            raise UserError(_(
                "Please generate the E-Waybill or mark the document as a Challan to print it."
            ))

        return self._generate_and_attach_pdf(_("Challan"))

    def _check_lines(self):
        if self.picking_id:
            error_message = []
            AccountMove = self.env['account.move']
            for line in self.move_ids:
                hsn_code = AccountMove._l10n_in_extract_digits(
                    line.product_id.l10n_in_hsn_code
                )
                if not hsn_code:
                    error_message.append(_(
                        "HSN code is not set in product %s",
                        line.product_id.name
                    ))
                elif not re.match("^[0-9]+$", hsn_code):
                    error_message.append(_(
                        "Invalid HSN Code (%(hsn_code)s) in product %(product)s",
                        hsn_code=hsn_code,
                        product=line.product_id.name,
                    ))
            return error_message
        return super()._check_lines()

    def _check_state(self):
        error_message = super()._check_state()
        if not self.picking_id:
            return error_message
        picking_state = self.picking_id.state
        if (not self._is_incoming() and picking_state != 'done') or (self._is_incoming() and picking_state not in ('done', 'assigned')):
            error_message.append(_(
                "An E-waybill cannot be generated for a %s document.",
                dict(self.env['stock.picking']._fields['state']._description_selection(self.env))[picking_state]
            ))
        return error_message

    def _l10n_in_tax_details_for_stock(self):
        tax_details = {
            'line_tax_details': defaultdict(dict),
            'tax_details': defaultdict(float)
        }
        for move in self.move_ids:
            line_tax_vals = self._l10n_in_tax_details_by_stock_move(move)
            tax_details['line_tax_details'][move.id] = line_tax_vals
            for val_field in ['total_excluded', 'total_included', 'total_void']:
                tax_details['tax_details'][val_field] += line_tax_vals[val_field]
            for tax in ['igst', 'cgst', 'sgst', 'cess_non_advol', 'cess', 'other']:
                for taxes in line_tax_vals['taxes']:
                    for field_key in ["rate", "amount"]:
                        if (key := f"{tax}_{field_key}") in taxes:
                            tax_details['tax_details'][key] += taxes[key]
        return tax_details

    def _l10n_in_tax_details_by_stock_move(self, move):
        taxes = move.ewaybill_tax_ids.compute_all(
            price_unit=move.ewaybill_price_unit,
            quantity=move.quantity
        )
        for tax in taxes['taxes']:
            tax_id = self.env['account.tax'].browse(tax['id'])
            tax_name = "other"
            for gst_tax_name in ['igst', 'sgst', 'cgst']:
                if self.env.ref('l10n_in.tax_tag_%s' % (gst_tax_name)).id in tax['tag_ids']:
                    tax_name = gst_tax_name
            if self.env.ref('l10n_in.tax_tag_cess').id in tax['tag_ids']:
                tax_name = tax_id.amount_type != 'percent' and 'cess_non_advol' or 'cess'
            rate_key = '%s_rate' % tax_name
            amount_key = '%s_amount' % tax_name
            tax.setdefault(rate_key, 0)
            tax.setdefault(amount_key, 0)
            tax[rate_key] += tax_id.amount
            tax[amount_key] += tax['amount']
        return taxes

    def _get_l10n_in_ewaybill_line_details(self, line, tax_details):
        if self.picking_id:
            AccountMove = self.env['account.move']
            product = line.product_id
            line_details = {
                'productName': product.name[:100],
                'hsnCode': AccountMove._l10n_in_extract_digits(product.l10n_in_hsn_code),
                'productDesc': line.description_picking[:100] if line.description_picking else "",
                'quantity': line.quantity,
                'qtyUnit': (
                    line.product_uom.l10n_in_code
                    and line.product_uom.l10n_in_code.split('-')[0]
                    or 'OTH'
                ),
                'taxableAmount': AccountMove._l10n_in_round_value(tax_details['total_excluded']),
            }
<<<<<<< 455b6ae293e68ae48a752ff0825cb8431dd2bc43
            gst_types = ('sgst', 'cgst', 'igst')
            gst_tax_rates = {}
            for tax in tax_details.get('taxes'):
                for gst_type in gst_types:
                    if tax_rate := tax.get(f'{gst_type}_rate'):
                        gst_tax_rates.update({
                            f"{gst_type}Rate": AccountMove._l10n_in_round_value(tax_rate)
                        })
                if cess_rate := tax.get("cess_rate"):
                    line_details['cessRate'] = AccountMove._l10n_in_round_value(cess_rate)
                if cess_non_advol := tax.get("cess_non_advol_amount"):
                    line_details['cessNonadvol'] = AccountMove._l10n_in_round_value(
                        cess_non_advol
                    )
            line_details.update(
                gst_tax_rates
                or dict.fromkeys(
                    [f"{gst_type}Rate" for gst_type in gst_types],
                    0
                )
            )
            return line_details
        return super()._get_l10n_in_ewaybill_line_details(line, tax_details)
||||||| 4b29bdf7c3f57ff573b89a32c4b8229c5c6d0cbb
        ewaybill_json = {
                # document details
                "supplyType": self.supply_type,
                "subSupplyType": self.type_id.sub_type_code,
                "docType": self.type_id.code,
                "transactionType": get_transaction_type(
                    self.partner_bill_from_id,
                    self.partner_ship_from_id,
                    self.partner_bill_to_id,
                    self.partner_ship_to_id
                ),
                "transDistance": str(self.distance),
                "docNo": self.document_number,
                "docDate": fields.Date.context_today(self.with_context(tz='Asia/Kolkata'), self.document_date).strftime("%d/%m/%Y"),
                # bill details
                **prepare_details(
                    key_paired_function={
                        'Gstin': lambda p: p.commercial_partner_id.vat or "URP",
                        'TrdName': lambda p: p.commercial_partner_id.name,
                        'StateCode': lambda p, place: self._get_partner_state_code(p, is_to_state=place == 'to'),
                    }.items(),
                    partner_detail={'from': self.partner_bill_from_id, 'to': self.partner_bill_to_id}.items()
                ),
                # shipping details
                **prepare_details(
                    key_paired_function={
                        "Addr1": lambda p: p.street and p.street[:120] or "",
                        "Addr2": lambda p: p.street2 and p.street2[:120] or "",
                        "Place": lambda p: p.city and p.city[:50] or "",
                        "Pincode": lambda p: int(p.zip) if p.country_id.code == "IN" else 999999,
                    }.items(),
                    partner_detail={'from': self.partner_ship_from_id, 'to': self.partner_ship_to_id}.items()
                ),
                "actToStateCode": self._get_partner_state_code(self.partner_ship_to_id),
                "actFromStateCode": self._get_partner_state_code(self.partner_ship_from_id),
        }
        if self.type_id.sub_type_code == '8':
            ewaybill_json["subSupplyDesc"] = self.type_description
        return ewaybill_json

    def _prepare_ewaybill_transportation_json_payload(self):
        # only pass transporter details when value is exist
        return dict(
            filter(lambda kv: kv[1], {
                "transporterId": self.transporter_id.vat,
                "transporterName": self.transporter_id.name,
                "transMode": self.mode,
                "transDocNo": self.transportation_doc_no,
                "transDocDate": self.transportation_doc_date and self.transportation_doc_date.strftime("%d/%m/%Y"),
                "vehicleNo": self.vehicle_no,
                "vehicleType": self.vehicle_type,
            }.items())
        )
=======

        transaction_type = get_transaction_type(
            self.partner_bill_from_id,
            self.partner_ship_from_id,
            self.partner_bill_to_id,
            self.partner_ship_to_id
        )
        ewaybill_json = {
                # document details
                "supplyType": self.supply_type,
                "subSupplyType": self.type_id.sub_type_code,
                "docType": self.type_id.code,
                "transactionType": transaction_type,
                "transDistance": str(self.distance),
                "docNo": self.document_number,
                "docDate": fields.Date.context_today(self.with_context(tz='Asia/Kolkata'), self.document_date).strftime("%d/%m/%Y"),
                # bill details
                **prepare_details(
                    key_paired_function={
                        'Gstin': lambda p: p.commercial_partner_id.vat or "URP",
                        'TrdName': lambda p: p.commercial_partner_id.name,
                        'StateCode': lambda p, place: self._get_partner_state_code(p, is_to_state=place == 'to'),
                    }.items(),
                    partner_detail={'from': self.partner_bill_from_id, 'to': self.partner_bill_to_id}.items()
                ),
                # shipping details
                **prepare_details(
                    key_paired_function={
                        "Addr1": lambda p: p.street and p.street[:120] or "",
                        "Addr2": lambda p: p.street2 and p.street2[:120] or "",
                        "Place": lambda p: p.city and p.city[:50] or "",
                        "Pincode": lambda p: int(p.zip) if p.country_id.code == "IN" else 999999,
                    }.items(),
                    partner_detail={'from': self.partner_ship_from_id, 'to': self.partner_ship_to_id}.items()
                ),
                "actToStateCode": self._get_partner_state_code(self.partner_ship_to_id),
                "actFromStateCode": self._get_partner_state_code(self.partner_ship_from_id),
        }
        if self.type_id.sub_type_code == '8':
            ewaybill_json["subSupplyDesc"] = self.type_description
        if transaction_type in (2, 4) and fields.Date.context_today(self) >= date(2026, 8, 1):
            ewaybill_json.update({
                "shipToGSTIN": self.partner_ship_to_id.commercial_partner_id.vat or "URP",
                "shipToTradeName": self.partner_ship_to_id.commercial_partner_id.name,
            })
        return ewaybill_json

    def _prepare_ewaybill_transportation_json_payload(self):
        # only pass transporter details when value is exist
        return dict(
            filter(lambda kv: kv[1], {
                "transporterId": self.transporter_id.vat,
                "transporterName": self.transporter_id.name,
                "transMode": self.mode,
                "transDocNo": self.transportation_doc_no,
                "transDocDate": self.transportation_doc_date and self.transportation_doc_date.strftime("%d/%m/%Y"),
                "vehicleNo": self.vehicle_no,
                "vehicleType": self.vehicle_type,
            }.items())
        )
>>>>>>> 5478122285e5c29700791dd4deab8f24e0dea376

    def _prepare_ewaybill_tax_details_json_payload(self):
        if self.picking_id:
            tax_details = self._l10n_in_tax_details_for_stock()
            round_value = self.env['account.move']._l10n_in_round_value
            return {
                'itemList': [
                    self._get_l10n_in_ewaybill_line_details(
                        line, tax_details['line_tax_details'][line.id]
                    )
                    for line in self.move_ids
                ],
                'totalValue': round_value(tax_details['tax_details'].get('total_excluded', 0.00)),
                **{
                    f'{tax_type}Value': round_value(
                        tax_details.get('tax_details').get(f'{tax_type}_amount', 0.00)
                    )
                    for tax_type in ['cgst', 'sgst', 'igst', 'cess']
                },
                'cessNonAdvolValue': round_value(
                    tax_details.get('cess_non_advol_amount', 0.00)
                ),
                'otherValue': round_value(
                    tax_details.get('other_amount', 0.00)
                ),
                'totInvValue': round_value(
                    tax_details['tax_details'].get('total_included', 0.00)
                ),
            }
        return super()._prepare_ewaybill_tax_details_json_payload()

    def _prepare_ewaybill_base_json_payload(self):
        ewaybill_json = super()._prepare_ewaybill_base_json_payload()
        if self.picking_id and self.type_id.sub_type_code == '8':
            ewaybill_json["subSupplyDesc"] = self.type_description
        return ewaybill_json
