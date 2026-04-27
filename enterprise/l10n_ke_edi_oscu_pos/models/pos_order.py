from datetime import datetime
from zoneinfo import ZoneInfo

from odoo import _, api, models, modules, fields, tools
from odoo.exceptions import UserError
from odoo.tools.float_utils import json_float_round

TAX_CODE_LETTERS = ['A', 'B', 'C', 'D', 'E']


def format_etims_datetime(dt):
    """ Format a UTC datetime as expected by eTIMS (only digits, Kenyan timezone). """
    return dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('Africa/Nairobi')).strftime('%Y%m%d%H%M%S')


def parse_etims_datetime(dt_str):
    """ Parse a datetime string received from eTIMS into a UTC datetime. """
    return datetime.strptime(dt_str, '%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('Africa/Nairobi')).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_ke_payment_method_id = fields.Many2one(
        string="eTIMS Payment Method",
        comodel_name='l10n_ke_edi_oscu.code',
        domain=[('code_type', '=', '07')],
        help="Method of payment communicated to the KRA via eTIMS. This is required when confirming purchases.",
    )

    l10n_ke_oscu_confirmation_datetime = fields.Datetime(string="Confirmation Date", copy=False)
    l10n_ke_oscu_receipt_number = fields.Integer(string="ETims Receipt Number", copy=False)
    l10n_ke_oscu_order_number = fields.Integer(string="ETims Number", copy=False)
    l10n_ke_oscu_signature = fields.Char(string="Signature", copy=False)
    l10n_ke_oscu_datetime = fields.Datetime(string="Signing Time", copy=False)
    l10n_ke_oscu_internal_data = fields.Char(string="Internal Data", copy=False)
    l10n_ke_control_unit = fields.Char(string="Control Unit ID")
    l10n_ke_order_json = fields.Json(string="Order JSON", copy=False)
    l10n_ke_order_send_status = fields.Selection(string="ETims status", selection=[('not_sent', "Not sent"), ('sent', "Sent")],
                                                 compute="_compute_send_status", store=True, readonly=True, copy=False)

    ###################################################
    # Compute                                         #
    ###################################################

    @api.depends("l10n_ke_oscu_order_number")
    def _compute_send_status(self):
        for order in self:
            order.l10n_ke_order_send_status = 'sent' if order.l10n_ke_oscu_order_number else 'not_sent'

    ###################################################
    # eTims                                           #
    ###################################################

    def post_order_to_etims(self):
        company = self.company_id
        content = self._l10n_ke_oscu_json_from_pos_order()

        if not (sequence := self.env['ir.sequence'].search([
            ('code', '=', 'l10n.ke.oscu.sale.sequence'),
            ('company_id', '=', company.id),
        ])):
            sequence = self.env['ir.sequence'].create({
                'name': 'eTIMS Customer Invoice Number',
                'implementation': 'no_gap',
                'company_id': company.id,
                'code': 'l10n.ke.oscu.sale.sequence',
            })

        content['invcNo'] = sequence.next_by_id()

        if not self.failed_pickings:
            error, data, _date = company._l10n_ke_call_etims('saveTrnsSalesOsdc', content)
        else:
            error = {
                'code': 'Out of stock',
                'message': _('One or more product(s) are out of stock.')
            }

        if not error:
            self.write({
                'l10n_ke_oscu_receipt_number': data['curRcptNo'],
                'l10n_ke_oscu_order_number': content['invcNo'],
                'l10n_ke_oscu_signature': data['rcptSign'],
                'l10n_ke_oscu_datetime': parse_etims_datetime(data['sdcDateTime']),
                'l10n_ke_oscu_internal_data': data['intrlData'],
                'l10n_ke_control_unit': company.l10n_ke_control_unit,
                'l10n_ke_order_json': content,
            })

            for pick in self.picking_ids:
                pick.move_ids._l10n_ke_oscu_process_moves()

            if self.is_invoiced and self.account_move:
                # As the order has been sent, no need to send the invoice as well, just copy the fields
                self._copy_etims_vals_from_pos_order_to_invoice(self.account_move)

                template = self.env.ref('account.email_template_edi_invoice')
                self.account_move.with_context(skip_invoice_sync=True)._generate_and_send(template)
        else:
            self.write({
                'l10n_ke_order_json': content,
            })
            # Just in case of error, we don't want to create gaps in the sequence
            sequence.number_next -= 1
            # If there is an error, we want to be sure the sequence and the l10n_ke_order_json are commited in the db before throwing the error
            if self._can_commit():
                self.env.cr.commit()

        return {
            "content": content,
            "error": error,
        }

    def _l10n_ke_oscu_get_json_from_order_lines(self):
        """ Return the values that should be sent to eTIMS for the lines in self. """
        self.ensure_one()
        lines_values = []
        for index, line in enumerate(self.lines):
            product = line.product_id  # for ease of reference
            product_uom_qty = line.product_uom_id._compute_quantity(line.qty, product.uom_id)

            if line.qty and line.discount != 100:
                # By computing the price_unit this way, we ensure that we get the price before the VAT tax, regardless of what
                # other price_include / price_exclude taxes are defined on the product.
                price_subtotal_before_discount = line.price_subtotal / (1 - (line.discount / 100))
                price_unit = price_subtotal_before_discount / line.qty
            else:
                price_unit = line.price_unit
                price_subtotal_before_discount = price_unit * line.qty
            discount_amount = price_subtotal_before_discount - line.price_subtotal

            line_values = {
                'itemSeq':   index + 1,                                             # Line number
                'itemCd':    product.l10n_ke_item_code,                             # Item code as defined by us, of the form KE2BFTNE0000000000000039
                'itemClsCd': product.unspsc_code_id.code,                           # Item classification code, in this case the UNSPSC code
                'itemNm':    line.name,                                             # Item name
                'pkgUnitCd': product.l10n_ke_packaging_unit_id.code,                # Packaging code, describes the type of package used
                'pkg':       product_uom_qty / product.l10n_ke_packaging_quantity,  # Number of packages used
                'qtyUnitCd': line.product_uom_id.l10n_ke_quantity_unit_id.code,     # The UOMs as defined by the KRA, defined seperately from the UOMs on the line
                'qty':       line.qty,
                'prc':       price_unit,
                'splyAmt':   price_subtotal_before_discount,
                'dcRt':      line.discount,
                'dcAmt':     discount_amount,
                'taxTyCd':   line.tax_ids.l10n_ke_tax_type_id.code,
                'taxblAmt':  line.price_subtotal,
                'taxAmt':    line.price_subtotal_incl - line.price_subtotal,
                'totAmt':    line.price_subtotal_incl,
            }

            fields_to_round = ('pkg', 'qty', 'prc', 'splyAmt', 'dcRt', 'dcAmt', 'taxblAmt', 'taxAmt', 'totAmt')
            for field in fields_to_round:
                line_values[field] = json_float_round(line_values[field], 2)

            fields_to_abs = ('pkg', 'qty', 'splyAmt', 'taxblAmt', 'taxAmt', 'totAmt')
            for field in fields_to_abs:
                line_values[field] = abs(line_values[field])

            if product.barcode:
                line_values.update({'bcd': product.barcode})

            lines_values.append(line_values)
        return lines_values

    def _l10n_ke_oscu_json_from_pos_order(self):
        """ Get the json content of the TrnsSalesSaveWr request from a pos order. """
        self.ensure_one()

        self.l10n_ke_oscu_confirmation_datetime = fields.Datetime.now()
        confirmation_datetime = format_etims_datetime(self.l10n_ke_oscu_confirmation_datetime)
        order_date = (self.date_order and self.date_order.strftime('%Y%m%d')) or ''
        order_number = self.sequence_number
        line_items = self._l10n_ke_oscu_get_json_from_order_lines()

        tax_codes, tax_rates, taxable_amounts, tax_amounts = self.env["account.move"]._get_taxes_data(line_items)

        content = {
            'invcNo':           '',                                         # KRA Invoice Number (set at the point of sending)
            'trdInvcNo':        (self.name or '')[:50],                     # Trader system pos order number
            'orgInvcNo':        order_number,                               # Original pos order number
            'cfmDt':            confirmation_datetime,                      # Validated date
            'pmtTyCd':          self.l10n_ke_payment_method_id.code or '',  # Payment type code
            'rcptTyCd': 'S' if not self.refunded_order_id else 'R',         # Receipt code
            **taxable_amounts,
            **tax_amounts,
            **tax_rates,
            'totTaxblAmt':      json_float_round(self.amount_total - self.amount_tax, 2),    # amount without taxes
            'totTaxAmt':        json_float_round(self.amount_tax, 2),                        # only taxes
            'totAmt':           json_float_round(self.amount_total, 2),                      # total amount with taxes
            'totItemCnt':       len(line_items),                                                          # Total Item count
            'itemList':         line_items,
            **self.company_id._l10n_ke_get_user_dict(self.create_uid, self.write_uid),
        }

        self.env["account.move"]._update_receipt_content(content, confirmation_datetime, order_date, self.partner_id)

        fields_to_abs = ('totTaxblAmt', 'totTaxAmt', 'totAmt')
        for field in fields_to_abs:
            content[field] = abs(content[field])

        if self.refunded_order_id:
            content.update({'rfdRsnCd': '06'})
        return content

    ###################################################
    # OVERRIDES                                       #
    ###################################################

    def _generate_pos_order_invoice(self):
        if self.config_id.is_kenyan:
            return super(PosOrder, self.with_context(generate_pdf=self.l10n_ke_oscu_order_number))._generate_pos_order_invoice()
        return super()._generate_pos_order_invoice()

    def _create_invoice(self, move_vals):
        invoice = super()._create_invoice(move_vals)
        if self.config_id.is_kenyan and self.l10n_ke_order_send_status == 'sent':
            self._copy_etims_vals_from_pos_order_to_invoice(invoice)
            invoice.message_post(body="This invoice has already been sent to eTIMS from the linked POS order.")
        return invoice

    ###################################################
    # ACTION                                          #
    ###################################################

    def action_post_order(self):
        etims_response = self.post_order_to_etims()
        if etims_response.get('error'):
            raise UserError(f"{etims_response['error']['code']} : {etims_response['error']['message']}")

    def action_post_selected_orders(self, order_ids):
        orders = self.env['pos.order'].browse(order_ids)
        errors = []
        for order in orders:
            if order.l10n_ke_order_send_status == 'not_sent':
                etims_response = order.post_order_to_etims()
                if etims_response.get('error'):
                    errors.append(etims_response.get('error'))

        if len(errors):
            raise UserError("One or more order(s) have failed, you might want to check them individually.")

    ###################################################
    # Helpers                                         #
    ###################################################

    def _get_l10n_ke_edi_oscu_pos_qrurl(self):
        self.ensure_one()
        res = self._l10n_ke_oscu_get_receipt_url() if self.l10n_ke_order_send_status == 'sent' else None
        return res

    def _l10n_ke_oscu_get_receipt_url(self):
        self.ensure_one()
        domain = 'etims-sbx' if self.company_id.l10n_ke_server_mode == 'test' else 'etims'
        data = f'{self.company_id.vat}{self.company_id.l10n_ke_branch_code}{self.l10n_ke_oscu_signature}'
        return f'https://{domain}.kra.go.ke/common/link/etims/receipt/indexEtimsReceiptData?Data={data}'

    def get_l10n_ke_edi_oscu_pos_data(self):
        """ Return the needed eTims data to the JS to be included in the receipt """
        self.ensure_one()
        return {
            "l10n_ke_edi_oscu_pos_date": self.l10n_ke_oscu_confirmation_datetime,
            "l10n_ke_edi_oscu_pos_receipt_number": self.l10n_ke_oscu_receipt_number,
            "l10n_ke_edi_oscu_pos_internal_data": self.l10n_ke_oscu_internal_data,
            "l10n_ke_edi_oscu_pos_signature": self.l10n_ke_oscu_signature,
            "l10n_ke_edi_oscu_pos_order_json": self.l10n_ke_order_json,
            "l10n_ke_edi_oscu_pos_serial_number": self.env.company.l10n_ke_oscu_serial_number,
            "l10n_ke_edi_oscu_pos_qrurl": self._get_l10n_ke_edi_oscu_pos_qrurl(),
        }

    def _copy_etims_vals_from_pos_order_to_invoice(self, invoice):
        """ Copy the etims fields in self on the invoice """
        invoice.write({
            'l10n_ke_control_unit': self.l10n_ke_control_unit,
            'l10n_ke_oscu_confirmation_datetime': self.l10n_ke_oscu_confirmation_datetime,
            'l10n_ke_oscu_datetime': self.l10n_ke_oscu_datetime,
            'l10n_ke_oscu_internal_data': self.l10n_ke_oscu_internal_data,
            'l10n_ke_oscu_receipt_number': self.l10n_ke_oscu_receipt_number,
            'l10n_ke_oscu_invoice_number': self.l10n_ke_oscu_order_number,
            'l10n_ke_oscu_signature': self.l10n_ke_oscu_signature,
            'l10n_ke_payment_method_id': self.l10n_ke_payment_method_id,
        })

    @staticmethod
    def _can_commit():
        return not tools.config['test_enable'] and not modules.module.current_test
