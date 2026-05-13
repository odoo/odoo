import json
from urllib.parse import urlencode

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import BinaryBytes

from odoo.addons.l10n_eg_edi_eta.models.account_edi_format import ETA_DOMAINS
from odoo.addons.l10n_eg_edi_eta.tools.eta_serialize import compute_eta_uuid


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_eg_edi_pos_enable = fields.Boolean(related='config_id.l10n_eg_edi_pos_enable')
    l10n_eg_edi_pos_state = fields.Selection(
        selection=[
            ('to_send', "To Send"),
            ('sent', "Sent"),
            ('sent_test', "Sent (Test)"),
            ('error', "Error"),
            ('error_test', "Error (Test)"),
            ('rejected', "Rejected"),
            ('rejected_test', "Rejected (Test)"),
        ],
        string="ETA State",
        copy=False,
        tracking=True,
    )
    l10n_eg_edi_pos_uuid = fields.Char(string="ETA UUID", copy=False, readonly=True)
    l10n_eg_edi_pos_submission_uuid = fields.Char(string="ETA Submission UUID", copy=False, readonly=True)
    l10n_eg_edi_pos_error = fields.Text(string="ETA Error", copy=False, readonly=True)
    l10n_eg_edi_pos_qr = fields.Char(string="ETA QR", copy=False, readonly=True)
    l10n_eg_edi_pos_json_doc_file = fields.Binary(
        string="ETA JSON Document",
        attachment=True,
        copy=False,
    )

    def action_pos_order_paid(self):
        if (
            self.country_code == 'EG'
            and self.config_id.l10n_eg_edi_pos_enable
            and not self.refunded_order_id
            and self.partner_id.is_company
        ):
            raise UserError(_("You're not allowed to issue sales receipts to business buyers."))

        result = super().action_pos_order_paid()
        if (
            self.country_code == 'EG'
            and self.config_id.l10n_eg_edi_pos_enable
            and self.l10n_eg_edi_pos_state not in ('sent', 'sent_test')
        ):
            self._l10n_eg_edi_pos_send()
        return result

    def _l10n_eg_edi_pos_state_for(self, state):
        if state in ('sent', 'error', 'rejected') and self.config_id.l10n_eg_edi_pos_preprod:
            return f'{state}_test'
        return state

    def _l10n_eg_edi_pos_send(self):
        """
            return the errors of the sending
        """
        self.ensure_one()

        if errors := self._l10n_eg_edi_pos_check_data():
            self.write({
                'l10n_eg_edi_pos_state': self._l10n_eg_edi_pos_state_for('error'),
                'l10n_eg_edi_pos_error': "\n".join(errors),
                'to_invoice': False,
            })
            return self.l10n_eg_edi_pos_error

        payload = self._l10n_eg_edi_pos_build_receipt()
        receipt_uuid = compute_eta_uuid(payload)
        payload['header']['uuid'] = receipt_uuid
        token, error = self.config_id._l10n_eg_edi_pos_get_token()
        if error:
            self.write({
                'l10n_eg_edi_pos_state': self._l10n_eg_edi_pos_state_for('error'),
                'l10n_eg_edi_pos_error': error,
                'to_invoice': False,
            })
            return error

        self.l10n_eg_edi_pos_uuid = receipt_uuid
        response = self._l10n_eg_edi_pos_post_submission(payload, token)
        envelope = {'request': payload, 'response': response.get('data') or {}}
        self.l10n_eg_edi_pos_json_doc_file = BinaryBytes(json.dumps(envelope, ensure_ascii=False, indent=2).encode())
        self.invalidate_recordset(fnames=['l10n_eg_edi_pos_json_doc_file'])
        error_message = self._l10n_eg_edi_pos_postprocess_response(response)
        if not error_message:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('res_field', '=', 'l10n_eg_edi_pos_json_doc_file'),
            ], limit=1)
            self.message_post(
                body=_("Receipt submitted to ETA."),
                attachment_ids=attachment.ids,
            )
        return error_message

    def _l10n_eg_edi_pos_build_receipt_request(self, payload, token):
        self.ensure_one()
        return {
            'body': json.dumps({
                'receipts': [payload],
                'signatures': self._l10n_eg_edi_pos_get_signatures(),
            }, ensure_ascii=False).encode('utf-8'),
            'header': {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        }

    def _l10n_eg_edi_pos_post_submission(self, payload, token):
        self.ensure_one()
        request_data = self._l10n_eg_edi_pos_build_receipt_request(payload, token)
        return self.env['account.edi.format']._l10n_eg_eta_connect_to_server(
            request_data,
            '/api/v1/receiptsubmissions',
            'POST',
            production_enviroment=not self.config_id.l10n_eg_edi_pos_preprod,
        )

    def action_l10n_eg_edi_pos_resend(self):
        self.ensure_one()
        if error := self._l10n_eg_edi_pos_send():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': _("ETA Submission Failed"),
                    'message': error,
                    'sticky': True,
                },
            }
        return False

    def download_l10n_eg_edi_pos_json_doc_file(self):
        self.ensure_one()
        if not self.l10n_eg_edi_pos_json_doc_file:
            raise UserError(_("No ETA submission has been recorded yet for this receipt."))
        params = {
            'model': self._name,
            'id': self.id,
            'field': 'l10n_eg_edi_pos_json_doc_file',
            'filename': self._l10n_eg_edi_pos_get_json_attachment_name(),
            'mimetype': 'application/json',
            'download': 'true',
        }
        return {'type': 'ir.actions.act_url', 'url': '/web/content/?' + urlencode(params), 'target': 'new'}

    def _l10n_eg_edi_pos_get_json_attachment_name(self):
        return f"ereceipt_{self.name.replace('/', '_')}.json"

    def _l10n_eg_edi_pos_build_receipt(self):
        self.ensure_one()
        edi_format = self.env['account.edi.format']
        journal = self.sale_journal
        branch = journal.l10n_eg_branch_id
        item_data, global_discounts, totals, tax_totals = self._l10n_eg_edi_pos_build_item_data()
        return {
            'header': self._l10n_eg_edi_pos_build_header(),
            'documentType': {'receiptType': 'r' if self.refunded_order_id else 'S', 'typeVersion': '1.2'},
            'seller': {
                'rin': branch.vat or '',
                'companyTradeName': branch.name or '',
                'branchCode': journal.l10n_eg_branch_identifier or '',
                'branchAddress': {
                    'country': branch.country_id.code or '',
                    'governate': branch.state_id.name or '',
                    'regionCity': branch.city or '',
                    'street': branch.street or '',
                    'buildingNumber': branch.l10n_eg_building_no or '',
                    'postalCode': branch.zip or '',
                },
                'deviceSerialNumber': self.config_id.sudo().l10n_eg_edi_pos_serial_number or '',
                'activityCode': journal.l10n_eg_activity_type_id.code or '',
            },
            'buyer': self._l10n_eg_edi_pos_build_buyer(),
            'itemData': item_data,
            'extraReceiptDiscountData': global_discounts,
            'totalSales': edi_format._l10n_eg_edi_round(totals['total_sale']),
            'netAmount': edi_format._l10n_eg_edi_round(totals['total_net']),
            'totalAmount': edi_format._l10n_eg_edi_round(totals['total'] - totals['total_extra_discount']),
            'taxTotals': list(tax_totals.values()),
            'paymentMethod': self._l10n_eg_edi_pos_get_payment_method(),
            'totalCommercialDiscount': edi_format._l10n_eg_edi_round(totals['total_discount']),
        }

    def _l10n_eg_edi_pos_build_header(self):
        self.ensure_one()
        if self.currency_id == self.company_id.currency_id:
            exchange_rate = 0
        else:
            amount_local = self.currency_id._convert(
                self.amount_total, self.company_id.currency_id, self.company_id, self.date_order,
            )
            exchange_rate = abs(amount_local / self.amount_total) if self.amount_total else 0
        header = {
            'dateTimeIssued': self.date_order.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'receiptNumber': self.pos_reference or '',
            'uuid': '',
            'currency': self.currency_id.name,
            'exchangeRate': exchange_rate,
            'sOrderNameCode': self.name,
            'orderdeliveryMode': 'FC',
            'grossWeight': 0.0,
            'netWeight': 0.0,
        }
        last_uuid = self.config_id.sudo().l10n_eg_edi_pos_last_uuid
        header['previousUUID'] = last_uuid or ""
        if self.l10n_eg_edi_pos_uuid:
            header['referenceOldUUID'] = self.l10n_eg_edi_pos_uuid
        if self.refunded_order_id:
            header['referenceUUID'] = self.refunded_order_id.l10n_eg_edi_pos_uuid
        return header

    def _l10n_eg_edi_pos_get_buyer_type(self):
        self.ensure_one()
        country_code = self.partner_id.commercial_partner_id.country_code
        return 'P' if not country_code or country_code == 'EG' else 'F'

    def _l10n_eg_edi_pos_build_buyer(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return {'type': 'P', 'paymentNumber': ''}
        buyer_type = self._l10n_eg_edi_pos_get_buyer_type()
        buyer = {'type': buyer_type, 'paymentNumber': ''}
        if self.amount_total >= self.company_id.l10n_eg_invoicing_threshold or buyer_type != 'P':
            if buyer_type != 'F':
                buyer['id'] = partner._get_additional_identifier('EG_NIN') or ''
            buyer['name'] = partner.name or ''
        return buyer

    def _l10n_eg_edi_pos_build_item_data(self):
        self.ensure_one()
        item_data, global_discounts = [], []
        totals = {'total': 0.0, 'total_net': 0.0, 'total_discount': 0.0, 'total_sale': 0.0, 'total_extra_discount': 0.0}
        tax_totals = {}
        edi_format = self.env['account.edi.format']
        for line in self.lines:
            price_unit = edi_format._l10n_eg_edi_round(line.price_unit, 2)
            rate_before_discount = (1 - line.discount / 100) if 0 < line.discount < 100 else 1
            net_sale = abs(edi_format._l10n_eg_edi_round(line.price_subtotal))
            line_total = abs(edi_format._l10n_eg_edi_round(line.price_subtotal_incl))
            total_sale = abs(edi_format._l10n_eg_edi_round(line.price_subtotal / rate_before_discount))
            if self.refunded_order_id or line.price_subtotal_incl >= 0:
                taxes = line.tax_ids_after_fiscal_position
                tax_details = taxes.compute_all(
                    price_unit * rate_before_discount,
                    self.currency_id,
                    line.qty,
                    product=line.product_id,
                    partner=self.partner_id,
                )
                taxable_items = []
                for tax_data in tax_details['taxes']:
                    tax = self.env['account.tax'].browse(tax_data['id'])
                    code_split = tax.l10n_eg_eta_code.split('_')
                    tax_type = code_split[0].upper()
                    sub_type = code_split[1].upper()
                    taxable_items.append({
                        'taxType': tax_type,
                        'amount': edi_format._l10n_eg_edi_round(abs(tax_data['amount'])),
                        'subType': sub_type,
                        'rate': abs(tax.amount) if tax.amount_type != 'fixed' else 0,
                    })
                    if tax.id not in tax_totals:
                        tax_totals[tax.id] = {'taxType': tax_type, 'amount': 0.0}
                    tax_totals[tax.id]['amount'] += abs(tax_data['amount'])
                discount_amount = edi_format._l10n_eg_edi_round(total_sale - net_sale)
                totals['total_discount'] += abs(discount_amount)
                totals['total_sale'] += total_sale
                totals['total_net'] += net_sale
                totals['total'] += line_total
                item_data.append({
                    'internalCode': str(line.product_id.id),
                    'description': line.full_product_name or line.product_id.display_name,
                    'itemType': 'GS1',
                    'itemCode': line.product_id.l10n_eg_eta_code or '',
                    'unitType': line.product_uom_id.l10n_eg_unit_code_id.code or '',
                    'quantity': abs(line.qty),
                    'unitPrice': price_unit,
                    'netSale': net_sale,
                    'totalSale': total_sale,
                    'total': line_total,
                    'taxableItems': taxable_items,
                    'commercialDiscountData': [{
                        'amount': discount_amount,
                        'description': f"{line.discount}% Discount",
                        'rate': line.discount,
                    }] if line.discount else [],
                })
            else:
                totals['total_extra_discount'] += line_total
                global_discounts.append({
                    'amount': line_total,
                    'description': line.full_product_name or line.product_id.display_name,
                })
        for discount in global_discounts:
            discount['rate'] = edi_format._l10n_eg_edi_round(discount['amount'] / (totals['total_net'] / 100)) if totals['total_net'] else 0
        for tax_total in tax_totals.values():
            tax_total['amount'] = edi_format._l10n_eg_edi_round(tax_total['amount'])
        return item_data, global_discounts, totals, tax_totals

    def _l10n_eg_edi_pos_get_payment_method(self):
        self.ensure_one()
        if self.payment_ids:
            return self.payment_ids[0].payment_method_id.l10n_eg_edi_pos_payment_code or 'C'
        return 'C'

    def _l10n_eg_edi_pos_get_signatures(self):
        return [{'signatureType': 'I', 'value': ''}]

    def _l10n_eg_edi_pos_get_qr_url(self):
        self.ensure_one()
        if not self.l10n_eg_edi_pos_uuid:
            return ''
        domain_key = 'invoice.preproduction' if self.config_id.l10n_eg_edi_pos_preprod else 'invoice.production'
        portal = ETA_DOMAINS[domain_key].rstrip('/')
        seller_rin = self.sale_journal.l10n_eg_branch_id.vat or ''
        return "%s/receipts/search/%s/share/%s#Total:%s,IssuerRIN:%s" % (
            portal,
            self.l10n_eg_edi_pos_uuid,
            self.date_order.strftime('%Y-%m-%dT%H:%M:%SZ'),
            self.amount_total,
            seller_rin,
        )

    def _l10n_eg_edi_pos_postprocess_response(self, response):
        self.ensure_one()
        if error := response.get('error'):
            state = 'to_send' if response.get('blocking_level') == 'warning' else 'error'
            error_message = self._l10n_eg_edi_pos_flatten_error(error)
            self.write({
                'l10n_eg_edi_pos_state': self._l10n_eg_edi_pos_state_for(state),
                'l10n_eg_edi_pos_error': error_message,
                'l10n_eg_edi_pos_uuid': '',
                'to_invoice': False,
            })
            return error_message

        data = response.get('data') or {}
        receipt_uuid = self.l10n_eg_edi_pos_uuid

        # rejection
        if rejected := next((d for d in data.get('rejectedDocuments') or [] if d.get('uuid') == receipt_uuid), None):
            error_message = self._l10n_eg_edi_pos_flatten_error(rejected.get('error'))
            self.write({
                'l10n_eg_edi_pos_state': self._l10n_eg_edi_pos_state_for('rejected'),
                'l10n_eg_edi_pos_error': error_message,
                'to_invoice': False,
            })
            return error_message

        # acceptance
        if next((d for d in data.get('acceptedDocuments') or [] if d.get('uuid') == receipt_uuid), None):
            self.config_id.sudo().l10n_eg_edi_pos_last_uuid = receipt_uuid
            self.write({
                'l10n_eg_edi_pos_state': self._l10n_eg_edi_pos_state_for('sent'),
                'l10n_eg_edi_pos_submission_uuid': data.get('submissionId') or '',
                'l10n_eg_edi_pos_error': '',
            })
            self.l10n_eg_edi_pos_qr = self._l10n_eg_edi_pos_get_qr_url()
            return ''

        error_message = _("Unexpected response from ETA.")
        self.write({
            'l10n_eg_edi_pos_state': self._l10n_eg_edi_pos_state_for('error'),
            'l10n_eg_edi_pos_error': error_message,
            'l10n_eg_edi_pos_uuid': '',
            'to_invoice': False,
        })
        return error_message

    def _l10n_eg_edi_pos_flatten_error(self, payload):
        if not payload:
            return ''
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            return "\n".join(filter(None, (self._l10n_eg_edi_pos_flatten_error(v) for v in payload.values())))
        if isinstance(payload, list):
            return "- " + "\n- ".join(filter(None, (self._l10n_eg_edi_pos_flatten_error(v) for v in payload)))
        return str(payload)

    def _l10n_eg_edi_pos_check_data(self):
        self.ensure_one()
        errors = []
        edi_format = self.env['account.edi.format']
        journal = self.sale_journal
        branch = journal.l10n_eg_branch_id
        if not all([branch, journal.l10n_eg_branch_identifier, journal.l10n_eg_activity_type_id]):
            errors.append(_("The sales journal is missing ETA branch, branch identifier, or activity type."))

        if self.refunded_order_id:
            if self.refunded_order_id.l10n_eg_edi_pos_state not in ('sent', 'sent_test'):
                errors.append(_("The original receipt must be submitted to ETA before a return can be issued."))
            if self.refunded_order_id.partner_id != self.partner_id:
                errors.append(_("Customer on the return must match the original receipt."))
        elif any(line.qty < 0 for line in self.lines):
            errors.append(_("Negative quantities are only allowed on return orders created from the original receipt."))

        if not self.refunded_order_id and self.amount_total >= self.company_id.l10n_eg_invoicing_threshold and (
            not self.partner_id or (self._l10n_eg_edi_pos_get_buyer_type() == 'P' and not self.partner_id._get_additional_identifier('EG_NIN'))
        ):
            errors.append(_("As the order value is equal to or above the invoicing threshold, please select a customer and set their National ID."))
        if branch and self.partner_id and branch.vat and self.partner_id.vat == branch.vat:
            errors.append(_("Cannot issue a receipt to a partner with the same VAT as the branch."))
        if branch and not edi_format._l10n_eg_validate_info_address(branch):
            errors.append(_("The branch partner is missing required address fields."))

        for line in self.lines:
            if not line.product_uom_id.l10n_eg_unit_code_id.code:
                errors.append(_("Product %s has no ETA unit-of-measure code.", line.product_id.display_name))
            for tax in line.tax_ids_after_fiscal_position:
                if not tax.l10n_eg_eta_code:
                    errors.append(_("Tax %s has no ETA tax code.", tax.name))
        return errors
