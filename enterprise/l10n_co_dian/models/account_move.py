from pytz import timezone
from lxml import etree

from collections import defaultdict
import re

from odoo import models, fields, api, _
from odoo.addons.l10n_co_dian import xml_utils
from odoo.exceptions import UserError
from odoo.fields import datetime

DESCRIPTION_CREDIT_CODE = [
    ("1", "Devolución parcial de los bienes y/o no aceptación parcial del servicio"),
    ("2", "Anulación de factura electrónica"),
    ("3", "Rebaja total aplicada"),
    ("4", "Ajuste de precio"),
    ("5", "Descuento comercial por pronto pago"),
    ("6", "Descuento comercial por volumen de ventas")
]

DESCRIPTION_DEBIT_CODE = [
    ('1', 'Intereses'),
    ('2', 'Gastos por cobrar'),
    ('3', 'Cambio del valor'),
    ('4', 'Otros'),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_co_dian_show_support_doc_button = fields.Boolean(compute='_compute_l10n_co_dian_show_support_doc_button')
    l10n_co_dian_post_time = fields.Datetime(readonly=True, copy=False)

    l10n_co_dian_document_ids = fields.One2many(
        comodel_name='l10n_co_dian.document',
        inverse_name='move_id',
    )
    l10n_co_edi_cufe_cude_ref = fields.Char(
        string="CUFE/CUDE/CUDS",
        compute="_compute_l10n_co_dian_state_and_cufe",
        store=True,
        copy=False,
        help="Unique ID used by the DIAN to identify the invoice.",
    )
    l10n_co_dian_state = fields.Selection(
        selection=[
            ('invoice_sending_failed', "Sending Failed"),
            ('invoice_pending', "Pending"),
            ('invoice_rejected', "Rejected"),
            ('invoice_accepted', "Accepted"),
        ],
        compute="_compute_l10n_co_dian_state_and_cufe",
        store=True,
        copy=False,
    )
    l10n_co_dian_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute="_compute_l10n_co_dian_attachment",
    )
    l10n_co_dian_identifier_type = fields.Selection(
        selection=[
            ('cufe', 'CUFE'),
            ('cude', 'CUDE'),
            ('cuds', 'CUDS'),
        ],
        compute="_compute_l10n_co_dian_identifier_type",
    )
    l10n_co_dian_is_enabled = fields.Boolean(compute="_compute_l10n_co_dian_is_enabled")

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends('l10n_co_dian_document_ids.state', 'l10n_co_dian_document_ids.identifier')
    def _compute_l10n_co_dian_state_and_cufe(self):
        for move in self:
            move.l10n_co_dian_state = None
            move.l10n_co_edi_cufe_cude_ref = None
            if move.l10n_co_dian_document_ids:
                doc = move.l10n_co_dian_document_ids.sorted()[:1]
                move.l10n_co_dian_state = doc.state
                move.l10n_co_edi_cufe_cude_ref = doc.identifier if doc.state == 'invoice_accepted' else False

    @api.depends('l10n_co_dian_document_ids.state')
    def _compute_l10n_co_dian_attachment(self):
        for move in self:
            doc = move.l10n_co_dian_document_ids.sorted()[:1]
            if doc.state == 'invoice_accepted':
                move.l10n_co_dian_attachment_id = doc.attachment_id
            else:
                move.l10n_co_dian_attachment_id = False

    @api.depends('journal_id', 'move_type')
    def _compute_l10n_co_dian_identifier_type(self):
        for move in self:
            if move.journal_id.l10n_co_edi_debit_note or move.move_type == 'out_refund':
                move.l10n_co_dian_identifier_type = 'cude'  # Debit Notes, Credit Notes
            elif move.l10n_co_edi_is_support_document:
                move.l10n_co_dian_identifier_type = 'cuds'  # Support Documents (Vendor Bills)
            else:
                move.l10n_co_dian_identifier_type = 'cufe'  # Invoices

    @api.depends('state', 'move_type', 'l10n_co_dian_state')
    def _compute_l10n_co_dian_show_support_doc_button(self):
        for move in self:
            move.l10n_co_dian_show_support_doc_button = (
                move.l10n_co_dian_is_enabled
                and move.l10n_co_dian_state != 'invoice_accepted'
                and move.move_type in ('in_refund', 'in_invoice')
                and move.state == 'posted'
                and move.journal_id.l10n_co_edi_is_support_document
            )

    @api.depends('country_code', 'company_currency_id', 'move_type', 'company_id.l10n_co_dian_provider')
    def _compute_l10n_co_dian_is_enabled(self):
        """ Check whether or not the DIAN is needed on this invoice. """
        for move in self:
            move.l10n_co_dian_is_enabled = (
                move.country_code == "CO"
                and move.company_currency_id.name == "COP"
                and move.is_invoice()
                and move.company_id.l10n_co_dian_provider == 'dian'
            )

    # -------------------------------------------------------------------------
    # Extends
    # -------------------------------------------------------------------------

    def _post(self, soft=True):
        # EXTENDS account
        res = super()._post(soft=soft)
        for move in self.filtered('l10n_co_dian_is_enabled'):
            # naive local colombian datetime
            move.l10n_co_dian_post_time = fields.Datetime.to_string(datetime.now(tz=timezone('America/Bogota')))
        return res

    @api.depends('l10n_co_dian_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_co_dian_state in ('invoice_pending', 'invoice_accepted'):
                move.show_reset_to_draft_button = False

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.env.ref('l10n_co_dian.report_vendor_document', raise_if_not_found=False) and \
                self.l10n_co_edi_is_support_document and \
                self.move_type in ('in_refund', 'in_invoice'):
            return 'l10n_co_dian.report_vendor_document'
        elif self.l10n_co_dian_state == 'invoice_accepted' and self.l10n_co_dian_attachment_id:
            return 'l10n_co_dian.report_invoice_document'
        return super()._get_name_invoice_report()

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        # EXTENDS account_edi_ubl_cii
        ubl_profile = tree.findtext('{*}ProfileID')
        if ubl_profile and ubl_profile.startswith('DIAN 2.1'):
            return self.env['account.edi.xml.ubl_dian']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    @api.model
    def _get_mail_template(self):
        # EXTENDS 'account'
        self.ensure_one()
        mail_template = super()._get_mail_template()
        if self.country_code == 'CO':
            xmlid = 'l10n_co_dian.email_template_edi_credit_note' if self.move_type == 'out_refund' else 'l10n_co_dian.email_template_edi_invoice'
            return self.env.ref(xmlid, raise_if_not_found=False) or mail_template
        return mail_template

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def l10n_co_dian_action_send_bill_support_document(self):
        self.ensure_one()
        xml, errors = self.env['account.edi.xml.ubl_dian']._export_invoice(self)
        if errors:
            raise UserError(_("Error(s) when generating the UBL attachment:\n- %s", '\n- '.join(errors)))
        doc = self._l10n_co_dian_send_invoice_xml(xml)
        if doc.state == 'invoice_rejected':
            if self.env['account.move.send']._can_commit():
                self._cr.commit()
            raise UserError(_("Error(s) when sending the document to the DIAN:\n- %s",
                              "\n- ".join(doc.message_json['errors']) or doc.message_json['status']))

    def _l10n_co_dian_get_invoice_report_qr_code_value(self):
        """ Returns the value to be embedded inside the QR Code on the PDF report.
        For Support Documents, see section 12.2 ('Anexo-Tecnico-Documento-Soporte[...].pdf').
        Otherwise, see section 11.7 ('Anexo-Tecnico-[...]-1-9.pdf').
        """
        self.ensure_one()
        return xml_utils._get_qr_code_value(etree.fromstring(self.l10n_co_dian_attachment_id.raw), self.currency_id, self.l10n_co_edi_is_support_document)

    def _l10n_co_dian_get_extra_invoice_report_values(self):
        """ Get the values used to render the PDF """
        self.ensure_one()
        document = self.l10n_co_dian_document_ids.sorted()[:1]
        return {
            'barcode_src': f'/report/barcode/?barcode_type=QR&value="{self._l10n_co_dian_get_invoice_report_qr_code_value()}"&width=180&height=180',
            'signing_datetime': document.datetime.replace(microsecond=0),
            'identifier': document.identifier,
        }

    def _l10n_co_dian_get_invoice_prepayments(self):
        """ Collect the prepayments linked to an account.move (based on the partials)
        :returns: a list of dict of the form: [{'name', 'amount', 'date'}]
        """
        if not self.is_sale_document():
            return []
        lines = self.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        prepayment_by_move = defaultdict(float)
        source_exchange_move = {}
        for field in ('debit', 'credit'):
            for partial in lines[f'matched_{field}_ids'].sorted('exchange_move_id', reverse=True):
                counterpart_line = partial[f'{field}_move_id']
                # Aggregate the exchange difference amount
                if partial.exchange_move_id:
                    source_exchange_move[partial.exchange_move_id] = counterpart_line
                elif counterpart_line.move_id in source_exchange_move:
                    counterpart_line = source_exchange_move[counterpart_line.move_id]
                    if counterpart_line not in prepayment_by_move:
                        continue
                # Exclude the partials created after creating a credit note from an existing move
                if (
                    (counterpart_line.move_id.move_type == 'out_refund' and lines.move_type == 'out_invoice')
                    or (counterpart_line.move_id.move_type == 'out_invoice' and lines.move_type == 'out_refund')
                ):
                    continue
                prepayment_by_move[counterpart_line] += partial.amount
        return [
            {
                'name': line.name,
                'date': line.date,
                'amount': amount,
            }
            for line, amount in prepayment_by_move.items()
        ]

    def _l10n_co_dian_send_invoice_xml(self, xml):
        """ Main method called by the Send & Print wizard / on a Support Document
        It unlinks the previous rejected documents, create a new one, send it to DIAN and logs in the chatter
        if it is accepted.
        """
        self.ensure_one()
        self.l10n_co_dian_document_ids.filtered(lambda doc: doc.state == 'invoice_rejected').unlink()
        document = self.env['l10n_co_dian.document']._send_to_dian(xml=xml, move=self)
        if document.state == 'invoice_accepted':
            self.with_context(no_new_invoice=True).message_post(
                body=_(
                    "The %s was accepted by the DIAN.",
                    dict(document.move_id._fields['move_type'].selection)[document.move_id.move_type],
                ) if not document.move_id.company_id.l10n_co_dian_demo_mode else _(
                    "The %s was validated locally in Demo Mode.",
                    dict(document.move_id._fields['move_type'].selection)[document.move_id.move_type],
                ),
                attachment_ids=document.attachment_id.copy().ids,
            )
        return document

    def _l10n_co_dian_get_attached_document_filename(self):
        self.ensure_one()
        # remove every non-word char or underscore, keep only the alphanumeric characters
        return re.sub(r'[\W_]', '', self.name)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_co_dian_net_price_subtotal(self):
        """ Returns the price subtotal after discount in company currency. """
        self.ensure_one()
        return self.move_id.direction_sign * self.balance

    def _l10n_co_dian_gross_price_subtotal(self):
        """ Returns the price subtotal without discount in company currency. """
        self.ensure_one()
        if self.discount == 100.0:
            return 0.0
        else:
            net_price_subtotal = self._l10n_co_dian_net_price_subtotal()
            return self.company_id.currency_id.round(net_price_subtotal / (1.0 - (self.discount or 0.0) / 100.0))
