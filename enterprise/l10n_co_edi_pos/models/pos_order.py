from lxml import etree

import json
import re

from pytz import timezone
from urllib.parse import quote

from odoo import api, fields, models
from odoo.addons.l10n_co_edi.models.account_invoice import L10N_CO_EDI_TYPE
from odoo.addons.l10n_co_dian import xml_utils
from odoo.exceptions import UserError
from odoo.tools.sql import column_exists, create_column

CUFE_CHUNK_SIZE = 32  # cufe len = 96 -> 3 chunks


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_co_edi_pos_name = fields.Char(string="DIAN Name")
    l10n_co_edi_pos_document_ids = fields.One2many(comodel_name='l10n_co_dian.document', inverse_name='pos_order_id')
    l10n_co_edi_pos_journal_id = fields.Many2one(comodel_name='account.journal', compute='_compute_l10n_co_edi_pos_journal_id')
    l10n_co_edi_pos_cufe_cude_ref = fields.Char(
        string="CUFE/CUDE/CUDS",
        compute="_compute_l10n_co_edi_pos_cufe_cude_ref",
        store=True,
        copy=False,
        help="Unique ID used by the DIAN to identify the invoice.",
    )

    l10n_co_edi_pos_attachment_id = fields.Many2one(comodel_name='ir.attachment', compute='_compute_from_current_document')
    l10n_co_edi_pos_dian_state = fields.Selection(compute='_compute_from_current_document', selection=[
        ('invoice_sending_failed', "Sending Failed"),  # webservice is not reachable
        ('invoice_pending', "Pending"),  # document was sent and the response is not yet known
        ('invoice_rejected', "Rejected"),
        ('invoice_accepted', "Accepted"),
    ])
    l10n_co_edi_pos_payment_option_id = fields.Many2one(comodel_name='l10n_co_edi.payment.option', compute='_compute_l10n_co_edi_pos_payment_option_id', store=True, readonly=False)
    l10n_co_edi_pos_dian_date = fields.Datetime(compute='_compute_l10n_co_edi_pos_dian_date')
    l10n_co_edi_pos_receipt_data = fields.Json(compute='_compute_l10n_co_edi_pos_receipt_data')

    l10n_co_edi_pos_enable_send = fields.Boolean(compute='_compute_l10n_co_edi_pos_enable_send')
    l10n_co_edi_pos_enable_invoice = fields.Boolean(compute='_compute_l10n_co_edi_pos_enable_invoice')

    def _auto_init(self):
        """
        Create all compute-stored fields here to avoid MemoryError when initializing on large databases.
        """
        if not column_exists(self.env.cr, 'pos_order', 'l10n_co_edi_pos_cufe_cude_ref'):
            create_column(self.env.cr, 'pos_order', 'l10n_co_edi_pos_cufe_cude_ref', 'varchar')

        if not column_exists(self.env.cr, 'pos_order', 'l10n_co_edi_pos_payment_option_id'):
            create_column(self.env.cr, 'pos_order', 'l10n_co_edi_pos_payment_option_id', 'int4')

        return super()._auto_init()

    def write(self, vals):
        # EXTEND point_of_sale
        for order in self:
            # Use the same condition as is used for the pos order name
            if vals.get('state') == 'paid' and order.name == '/' and order.company_id.l10n_co_edi_pos_dian_enabled:
                journal = order.l10n_co_edi_pos_journal_id
                if journal.l10n_co_edi_pos_is_final_consumer:
                    vals['l10n_co_edi_pos_name'] = journal.l10n_co_edi_pos_sequence_id.next_by_id()

        return super().write(vals)

    @api.depends('partner_id', 'amount_total')
    def _compute_l10n_co_edi_pos_journal_id(self):
        final_consumer = self.env.ref('l10n_co_edi.consumidor_final_customer', raise_if_not_found=False)
        for pos_order in self:
            if not pos_order.partner_id or pos_order.partner_id == final_consumer:
                pos_order.l10n_co_edi_pos_journal_id = pos_order.config_id.l10n_co_edi_final_consumer_invoices_journal_id
            elif pos_order.amount_total < 0.0:
                pos_order.l10n_co_edi_pos_journal_id = pos_order.config_id.l10n_co_edi_credit_note_journal_id
            else:
                pos_order.l10n_co_edi_pos_journal_id = pos_order.config_id.invoice_journal_id

    @api.depends('state', 'l10n_co_edi_pos_document_ids', 'company_id')
    def _compute_l10n_co_edi_pos_enable_send(self):
        for order in self:
            documents = order.l10n_co_edi_pos_document_ids
            invoice_accepted_exists = documents and any(doc.state == 'invoice_accepted' for doc in documents)
            order.l10n_co_edi_pos_enable_send = (order.company_id.l10n_co_edi_pos_dian_enabled
                                                 and order.state in ('paid', 'done')
                                                 and not invoice_accepted_exists)

    @api.depends('company_id.l10n_co_edi_pos_dian_enabled', 'state')
    def _compute_l10n_co_edi_pos_enable_invoice(self):
        for order in self:
            if order.company_id.l10n_co_edi_pos_dian_enabled:
                order.l10n_co_edi_pos_enable_invoice = False
            else:
                order.l10n_co_edi_pos_enable_invoice = order.state == 'paid'

    @api.depends('company_id.l10n_co_edi_pos_dian_enabled', 'payment_ids.payment_method_id')
    def _compute_l10n_co_edi_pos_payment_option_id(self):
        for order in self:
            if (order.company_id.l10n_co_edi_pos_dian_enabled
                    and order.payment_ids
                    and order.payment_ids[0].payment_method_id):
                order.l10n_co_edi_pos_payment_option_id = order.payment_ids[0].payment_method_id.l10n_co_edi_pos_payment_option_id
            else:
                order.l10n_co_edi_pos_payment_option_id = False

    @api.depends('amount_total')
    def _compute_l10n_co_edi_pos_invoice_or_refund(self):
        for pos_order in self:
            pos_order.l10n_co_edi_pos_is_refund = pos_order.amount_total < 0

            if pos_order.amount_total < 0:
                # Credit Note
                pos_order.l10n_co_edi_pos_edi_type = L10N_CO_EDI_TYPE['Credit Note']
                pos_order.l10n_co_edi_pos_identifier_type = 'cude'
                pos_order.l10n_co_edi_pos_operation_type = '20'
            else:
                # Invoice
                pos_order.l10n_co_edi_pos_edi_type = L10N_CO_EDI_TYPE['Sales Invoice']
                pos_order.l10n_co_edi_pos_identifier_type = 'cufe'
                pos_order.l10n_co_edi_pos_operation_type = '10'

    @api.depends('l10n_co_edi_pos_document_ids.state', 'l10n_co_edi_pos_document_ids.identifier')
    def _compute_l10n_co_edi_pos_cufe_cude_ref(self):
        for order in self:
            order.l10n_co_edi_pos_cufe_cude_ref = None
            if order.l10n_co_edi_pos_document_ids:
                doc = order.l10n_co_edi_pos_document_ids.sorted()[:1]
                order.l10n_co_edi_pos_cufe_cude_ref = doc.identifier if doc.state == 'invoice_accepted' else False

    @api.depends('l10n_co_edi_pos_document_ids.state')
    def _compute_from_current_document(self):
        for pos_order in self:
            doc = pos_order.l10n_co_edi_pos_document_ids.sorted()[:1]
            pos_order.l10n_co_edi_pos_dian_state = doc.state
            if doc.state == 'invoice_accepted':
                pos_order.l10n_co_edi_pos_attachment_id = doc.attachment_id
            else:
                pos_order.l10n_co_edi_pos_attachment_id = False

    @api.depends('date_order')
    def _compute_l10n_co_edi_pos_dian_date(self):
        for order in self:
            order.l10n_co_edi_pos_dian_date = fields.Datetime.to_string(order.date_order.now(tz=timezone('America/Bogota')))

    @api.depends('to_invoice', 'account_move.l10n_co_dian_state', 'partner_id',
                 'l10n_co_edi_pos_dian_state', 'l10n_co_edi_pos_journal_id', 'l10n_co_edi_pos_payment_option_id')
    def _compute_l10n_co_edi_pos_receipt_data(self):
        not_applicable_orders = self.filtered(
            # Could be the case when the generated invoice was not correctly sent to DIAN
            lambda po:
                not po.company_id.l10n_co_edi_pos_dian_enabled
                or (po.to_invoice and (not po.account_move or po.account_move.l10n_co_dian_state != 'invoice_accepted'))
                or (not po.to_invoice and po.l10n_co_edi_pos_dian_state != 'invoice_accepted')
        )

        not_applicable_orders.l10n_co_edi_pos_receipt_data = False
        final_consumer = self.env.ref('l10n_co_edi.consumidor_final_customer')
        regimen_selection_vals = dict(self.env['res.partner']._fields['l10n_co_edi_fiscal_regimen'].selection)

        for order in self - not_applicable_orders:
            # There will always be a partner when the pos order has been invoiced so we don't need to check for it here
            customer_partner_address = (order.partner_id or final_consumer).address_get(['invoice'])['invoice']
            customer_partner = self.env['res.partner'].browse(customer_partner_address)
            partner = order.company_id.partner_id
            partner_fiscal_regimen_value = regimen_selection_vals.get(partner.l10n_co_edi_fiscal_regimen)
            journal = order.l10n_co_edi_pos_journal_id

            if order.to_invoice:
                document = order.account_move.l10n_co_dian_document_ids.sorted()[:1]
                barcode_src = order.account_move._l10n_co_dian_get_extra_invoice_report_values()['barcode_src']
            else:
                document = order.l10n_co_edi_pos_document_ids.sorted()[:1]
                barcode_src = order._l10n_co_edi_pos_get_qr_code()

            data = {
                'l10n_co_edi_pos_receipt_data': {
                    'document_state': document.state,
                    'header': {
                        'l10n_co_edi_pos_payment_option_id': {
                            'code': order.l10n_co_edi_pos_payment_option_id.code,
                            'name': order.l10n_co_edi_pos_payment_option_id.name,
                        },
                        'l10n_co_edi_type': order._l10n_co_edi_type(),
                        'l10n_co_edi_dian_authorization_number': journal.l10n_co_edi_dian_authorization_number,
                        'l10n_co_edi_dian_authorization_date': fields.Date.to_string(journal.l10n_co_edi_dian_authorization_date),
                        'l10n_co_edi_dian_authorization_end_date': fields.Date.to_string(journal.l10n_co_edi_dian_authorization_end_date),
                        'l10n_co_edi_min_range_number': journal.l10n_co_edi_min_range_number,
                        'l10n_co_edi_max_range_number': journal.l10n_co_edi_max_range_number,
                        'sequence_number': order.l10n_co_edi_pos_name if not order.to_invoice else order.account_move.name,
                    },
                    'before_footer': {
                        'partner_name': customer_partner.name,
                        'identification_type': customer_partner.l10n_latam_identification_type_id.name,
                        'identification_number': customer_partner.vat,
                        'address': customer_partner.contact_address_complete,
                        'large_taxpayer': partner.l10n_co_edi_large_taxpayer,
                        'fiscal_regimen_description': partner_fiscal_regimen_value,
                        'obligation_type_description': partner.l10n_co_edi_obligation_type_ids.description,
                        'barcode_src': barcode_src,
                    },
                    'after_footer': {
                        'l10n_co_edi_pos_serial_number': order.config_id.l10n_co_edi_pos_serial_number,
                    }
                }
            }

            if document.state == 'invoice_accepted':
                root = etree.fromstring(document.attachment_id.raw)
                nsmap = {k: v for k, v in root.nsmap.items() if k}  # empty namespace prefix is not supported for XPaths

                if document.state == 'invoice_accepted':
                    cufe = document.identifier
                    cufe_chunks = [cufe[i:i + CUFE_CHUNK_SIZE] for i in range(0, len(cufe), CUFE_CHUNK_SIZE)]
                else:
                    cufe_chunks = []

                data['l10n_co_edi_pos_receipt_data']['after_footer'] |= {
                    'cufe_chunks': cufe_chunks,
                    'signing_time': fields.Datetime.to_string(document.datetime),
                    'issue_date': root.findtext('./cbc:IssueDate', namespaces=nsmap),
                    'issue_time': root.findtext('./cbc:IssueTime', namespaces=nsmap),
                }

            order.l10n_co_edi_pos_receipt_data = json.dumps(data['l10n_co_edi_pos_receipt_data'])

    def _l10n_co_edi_type(self):
        return '1' if not self._l10n_co_edi_is_refund() else '91'

    def _l10n_co_edi_operation_type(self):
        return '10' if not self._l10n_co_edi_is_refund() else '20'

    def _l10n_co_dian_identifier_type(self):
        return 'cufe' if not self._l10n_co_edi_is_refund() else 'cude'

    def _l10n_co_edi_is_refund(self):
        return self.amount_total < 0

    def _prepare_invoice_vals(self):
        # EXTENDS l10n_co_pos
        vals = super()._prepare_invoice_vals()

        if self.company_id.l10n_co_edi_pos_dian_enabled:
            vals.update({
                'l10n_co_edi_payment_option_id': self.l10n_co_edi_pos_payment_option_id.id,
                'journal_id': self.l10n_co_edi_pos_journal_id.id,
            })

            if self.l10n_co_edi_pos_name:
                vals.update({
                    'name': self.l10n_co_edi_pos_name,
                })

        return vals

    @api.model
    def sync_from_ui(self, orders):
        """Entrypoint for EDI through the POS. Launch EDI for all paid orders when they are received in the backend. Amend
        the response sent back to the POS after EDI to include fields needed for the receipt."""
        result = super().sync_from_ui(orders)

        # all orders in a single sync_from_ui call will belong to the same session
        if len(orders) > 0 and orders[0].get('session_id'):
            orders_to_send = [order['id'] for order in result['pos.order'] if order['state'] == 'paid' and not order['to_invoice']]
            for order_db in self.env['pos.order'].browse(orders_to_send):
                if order_db.company_id.l10n_co_edi_pos_dian_enabled and order_db.l10n_co_edi_pos_dian_state != 'invoice_accepted':
                    order_db.l10n_co_edi_pos_action_send_document()

            for order in result['pos.order']:
                extra_fields_needed_in_pos = ['l10n_co_edi_pos_receipt_data']
                order_db = self.env['pos.order'].browse(order['id'])
                order.update(order_db.read(extra_fields_needed_in_pos)[0])

        return result

    def l10n_co_edi_pos_action_send_document(self):
        # ANALOG _call_web_service_before_invoice_pdf_render in l10n_co_dian/account_move_send
        self.ensure_one()

        # Render
        xml, errors = self.env['pos.edi.xml.ubl_dian']._export_pos_order(self)
        if errors:
            raise UserError(self.env._("Error(s) when generating the UBL attachment:\n- %s", '\n- '.join(errors)))

        # Send to DIAN
        doc = self._l10n_co_edi_pos_send_pos_order_xml(xml)

        if doc.state == 'invoice_rejected':
            if self.env['account.move.send']._can_commit():
                self._cr.commit()
            raise UserError(self.env._("Error(s) when sending the document to the DIAN:\n- %s",
                              "\n- ".join(doc.message_json['errors']) or doc.message_json['status']))
        elif doc.state == 'invoice_accepted':
            # Call DIAN again
            attached_document, error_msg = doc._get_attached_document()

            if error_msg:
                if self.env['account.move.send']._can_commit():
                    self._cr.commit()
                raise UserError(self.env._("Error(s) when generating the Attached Document:\n- %s", error_msg))
            else:
                self.env['ir.attachment'].create([{
                    'raw': attached_document,
                    'name': self._l10n_co_edi_pos_get_attached_document_filename() + ".xml",
                    'res_model': 'pos.order',
                    'res_id': self.id,
                }])

    def _l10n_co_edi_pos_get_qr_code(self):
        self.ensure_one()

        value = xml_utils._get_qr_code_value(etree.fromstring(self.l10n_co_edi_pos_attachment_id.raw), self.currency_id)
        return f'/report/barcode/?barcode_type=QR&value={quote(value)}&width=180&height=180'

    def _l10n_co_edi_pos_send_pos_order_xml(self, xml):
        # ANALOG _l10n_co_dian_send_invoice_xml in l10n_co_dian/account_move
        self.ensure_one()
        self.l10n_co_edi_pos_document_ids.filtered(lambda doc: doc.state == 'invoice_rejected').unlink()
        document = self.env['l10n_co_dian.document']._l10n_co_edi_pos_send_to_dian(data={
            'xml': xml,
            'company_id': self.company_id,
            'is_sale_document': True,
            'record': self,
        })

        if document.state == 'invoice_accepted':
            self.message_post(
                body=self.env._("The POS Order was accepted by the DIAN."),
                attachment_ids=document.attachment_id.copy().ids,
            )

        return document

    def _l10n_co_edi_pos_get_attached_document_filename(self):
        self.ensure_one()
        # remove every non-word char or underscore, keep only the alphanumeric characters
        return re.sub(r'[\W_]', '', self.name)
