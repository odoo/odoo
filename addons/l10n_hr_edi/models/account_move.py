import logging
import pytz
import re

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL
from odoo.tools.sql import column_exists, create_column

from ..tools import (
    _mer_api_mark_paid,
    _mer_api_query_document_process_status_inbox,
    _mer_api_query_document_process_status_outbox,
    _mer_api_update_document_process_status,
    _mer_api_check_fiscalization_status_outbox,
    _mer_api_check_fiscalization_status_inbox,
    MojEracunServiceError,
)

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Fields required for correctly generating CIUS HR documents
    l10n_hr_process_type = fields.Selection(
        [
            ('P1', "P1: Issuing invoices for deliveries of goods and services according to purchase orders, based on contracts"),
            ('P2', "P2: Periodic invoicing for deliveries of goods and services based on contracts"),
            ('P3', "P3: Issuing invoices for delivery according to an independent purchase order"),
            ('P4', "P4: Prepayment (advance payment)"),
            ('P5', "P5: Payment on the spot (Sport payment)"),
            ('P6', "P6: Payment before delivery, based on purchase order"),
            ('P7', "P7: Issuing invoices with references to the delivery note"),
            ('P8', "P8: Issuing invoices with references to the shipping and receipt notes"),
            ('P9', "P9: Credits or invoices with negative amounts, issued for various reasons, including empty returns packaging"),
            ('P10', "P10: Issuing a corrective invoice (reversal/correction of invoice)"),
            ('P11', "P11: Issuing partial and final invoices"),
            ('P12', "P12: Self-issuance of invoice"),
            ('P99', "P99: Customer-defined process"),
        ],
        string="Business Process Type",
        compute='_compute_l10n_hr_process_type',
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_hr_customer_defined_process_name = fields.Char(
        string="Custom Process Name",
        help="Required when Process Type is P99. Specify the name of your custom business process. "
            "This will appear in the UBL as P99:YourProcessName",
    )
    l10n_hr_fiscal_user_id = fields.Many2one(
        comodel_name="res.partner",
        string="Fiscal User",
        domain=lambda self: self._get_l10n_hr_fiscal_user_id_domain(),
    )
    l10n_hr_operator_name = fields.Char(string="Operator Label", related='l10n_hr_fiscal_user_id.name')
    l10n_hr_operator_oib = fields.Char(string="Operator OIB", related='l10n_hr_fiscal_user_id.l10n_hr_personal_oib')
    # Additional fields
    l10n_hr_edi_addendum_id = fields.One2many(comodel_name='l10n_hr_edi.addendum', inverse_name='move_id', string='HR EDI Addendum', copy=False)
    l10n_hr_invoice_sending_time = fields.Datetime(related='l10n_hr_edi_addendum_id.invoice_sending_time')
    # EDI and fiscalization-specific fields
    l10n_hr_business_document_status = fields.Selection(related='l10n_hr_edi_addendum_id.business_document_status')
    l10n_hr_business_status_reason = fields.Char(related='l10n_hr_edi_addendum_id.business_status_reason')
    l10n_hr_fiscalization_number = fields.Char(related='l10n_hr_edi_addendum_id.fiscalization_number')
    l10n_hr_fiscalization_status = fields.Selection(related='l10n_hr_edi_addendum_id.fiscalization_status')
    l10n_hr_fiscalization_error = fields.Char(related='l10n_hr_edi_addendum_id.fiscalization_error')
    l10n_hr_fiscalization_request = fields.Char(related='l10n_hr_edi_addendum_id.fiscalization_request')
    l10n_hr_fiscalization_channel_type = fields.Selection(related='l10n_hr_edi_addendum_id.fiscalization_channel_type')
    # Payment reporting
    l10n_hr_payment_reported_amount = fields.Monetary(
        related='l10n_hr_edi_addendum_id.payment_reported_amount',
        currency_field='currency_id',
    )
    l10n_hr_payment_unreported = fields.Boolean(compute='_compute_l10n_hr_payment_unreported', search='_search_l10n_hr_payment_unreported')
    l10n_hr_payment_method_type = fields.Selection(related='l10n_hr_edi_addendum_id.payment_method_type', readonly=False)
    # MojEracun integration fields
    l10n_hr_mer_document_eid = fields.Char(related='l10n_hr_edi_addendum_id.mer_document_eid')
    l10n_hr_mer_document_status = fields.Selection(related='l10n_hr_edi_addendum_id.mer_document_status')

    def _auto_init(self):
        if not column_exists(self.env.cr, 'account_move', 'l10n_hr_process_type'):
            create_column(self.env.cr, 'account_move', 'l10n_hr_process_type', 'varchar')
        return super()._auto_init()

    @api.depends('l10n_hr_edi_addendum_id.payment_reported_amount', 'amount_residual', 'amount_total')
    def _compute_l10n_hr_payment_unreported(self):
        for move in self:
            move.l10n_hr_payment_unreported = move.l10n_hr_payment_reported_amount != (move.amount_total - move.amount_residual)

    def _search_l10n_hr_payment_unreported(self, operator, value):
        # A specific override to enable the "Has unreported payments" filter on the list view
        if operator == '!=':
            query = self._search([])
            query.join('account_move', 'id', 'l10n_hr_edi_addendum', 'move_id', 'addendum')
            query.add_where(SQL("""ROUND(%(payment_reported_amount)s - %(amount_total)s + %(amount_residual)s, 8) != 0""",
                payment_reported_amount=self.env['l10n_hr_edi.addendum']._field_to_sql('account_move__addendum', 'payment_reported_amount', query),
                amount_total=self._field_to_sql('account_move', 'amount_total', query),
                amount_residual=self._field_to_sql('account_move', 'amount_residual', query),
            ))
            return [('id', 'in', query)]
        return []

    @api.constrains('move_type', 'l10n_hr_process_type')
    def _check_l10n_hr_process_type(self):
        for record in self:
            if record.country_code == 'HR' and (record.l10n_hr_process_type == 'P9') == (record.move_type != 'out_refund'):
                raise ValidationError(self.env._('Business Process Type P9 can only be used with credit notes and vice versa.'))

    @api.depends('l10n_hr_fiscalization_status')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_hr_fiscalization_status:
                move.show_reset_to_draft_button = False

    @api.depends('move_type', 'l10n_hr_process_type')
    def _compute_l10n_hr_process_type(self):
        for move in self:
            if not move.l10n_hr_process_type:
                if move.move_type == 'out_refund':
                    move.l10n_hr_process_type = 'P9'
                elif move.move_type == 'out_invoice':
                    move.l10n_hr_process_type = 'P1'

    def _get_l10n_hr_fiscalization_number(self, name):
        """
        Extract the fiscal numbering triple (ex. 1/1/1) from the document name.
        Only applies for Croatian sales invoices/credit notes. Expected name
        pattern is produced by the overridden `sequence.mixin` logic.
        """
        name_regex = r'.*?(?P<seq>\d+)/(?P<premises_label>\d+)/(?P<device_label>\d+)'
        if match := re.match(name_regex, name):
            return f"{int(match.group('seq'))}/{match.group('premises_label')}/{match.group('device_label')}"
        else:
            return False

    def _get_l10n_hr_fiscal_user_id_domain(self):
        internal_users = self.env.ref('base.group_user')
        domain = [('user_ids', 'in', internal_users.users.ids)]
        return domain

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None:
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0':
                return self.env['account.edi.xml.ubl_hr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def _get_invoice_reference_odoo_invoice(self):
        """
        Override to propose a structured reference for HR domestic flows.
        When the company and partner are both in Croatia and the invoice has a
        computed fiscalization number, return a reference like:
          "HR00 {BrOznRacOznPosPrOznNapUr}"
        where slashes are removed per Croatian banking conventions.
        """
        self.ensure_one()
        # Check if invoice has fiscalization number, company is in Croatia, and partner is in Croatia
        if self.company_id.country_code == 'HR' and self.partner_id.country_code == 'HR':
            fisc_num_hr_format = re.sub(r'\D', '', self._get_l10n_hr_fiscalization_number(self.name))
            return "HR00 " + fisc_num_hr_format
        else:
            return super()._get_invoice_reference_odoo_invoice()

    def _get_l10n_hr_fiscal_user_id_domain(self):
        internal_users = self.env.ref('base.group_user')
        domain = [('user_ids', 'in', internal_users.users.ids)]
        return domain

    def _post(self, soft=True):
        for move in self:
            if move.country_code == 'HR' and move.is_sale_document():
                if not move.l10n_hr_fiscal_user_id:
                    move.l10n_hr_fiscal_user_id = move.env.user.partner_id
            if move.l10n_hr_mer_document_eid and move.is_purchase_document():
                if move.l10n_hr_business_document_status == '1':
                    raise UserError(self.env._("This vendor bill is already rejected according to the Tax Authority."))
                elif move.l10n_hr_business_document_status in ('4', '99'):
                    _mer_api_update_document_process_status(
                        move.company_id,
                        move.l10n_hr_mer_document_eid,
                        0,
                    )
                    move.l10n_hr_edi_addendum_id.business_document_status = '0'
                    _logger.info("Document eID %s reported as approved by recepient.", move.l10n_hr_mer_document_eid)
        return super()._post(soft=soft)

    def l10n_hr_edi_mer_action_reject(self):
        self.ensure_one()
        return {
            'name': self.env._("Reject MojEracun invoice"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'l10n_hr_edi.mojeracun_reject_wizard',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
        }

    def l10n_hr_edi_mer_action_fetch_status(self):
        """
        Fetch and update the status of a single document on MojEracun.
        """
        self.ensure_one()
        if self.is_sale_document():
            response_mer = _mer_api_query_document_process_status_outbox(self.company_id, electronic_id=self.l10n_hr_mer_document_eid)[0]
            response_fisc = _mer_api_check_fiscalization_status_outbox(self.company_id, electronic_id=self.l10n_hr_mer_document_eid)[0]
        elif self.is_purchase_document():
            response_mer = _mer_api_query_document_process_status_inbox(self.company_id, electronic_id=self.l10n_hr_mer_document_eid)[0]
            response_fisc = _mer_api_check_fiscalization_status_inbox(self.company_id, electronic_id=self.l10n_hr_mer_document_eid)[0]
        else:
            return
        self.l10n_hr_edi_addendum_id.write({
            'mer_document_status': str(response_mer.get('StatusId')),
            'business_document_status': str(response_mer.get('DocumentProcessStatusId')),
            'fiscalization_status': str(response_fisc['messages'][-1].get('status')),
            'fiscalization_error': str(response_fisc['messages'][-1].get('errorCode') + ' - ' + response_fisc['messages'][-1].get('errorCodeDescription')),
            'fiscalization_request': str(response_fisc['messages'][-1].get('fiscalizationRequestId')),
            'business_status_reason': str(response_fisc['messages'][-1].get('businessStatusReason')),
            'fiscalization_channel_type': str(response_fisc.get('channelType')),
        })

    def l10n_hr_edi_mer_action_report_paid(self):
        for move in self:
            if not move.l10n_hr_mer_document_eid:
                continue
            state_to_set = {'partial': '3', 'paid': '2'}.get(move.payment_state)
            amount_to_report = (move.amount_total - move.amount_residual) - move.l10n_hr_payment_reported_amount
            if amount_to_report and state_to_set:
                try:
                    response = _mer_api_mark_paid(
                        move.company_id,
                        move.l10n_hr_mer_document_eid,
                        fields.Datetime.now(pytz.timezone('Europe/Zagreb')).strftime('%Y-%m-%dT%H:%M:%S'),
                        amount_to_report,
                        move.l10n_hr_payment_method_type,
                    )
                except MojEracunServiceError:
                    _logger.error("Failed to report payments document: %s", move.l10n_hr_mer_document_eid)
                    continue
                move.l10n_hr_edi_addendum_id.payment_reported_amount += amount_to_report
                move.l10n_hr_edi_addendum_id.fiscalization_request = response.get('fiscalizationRequestId')
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": f"mojeracun_{response['electronicId']}_payment.xml",
                        "raw": response['encodedXml'],
                        "type": "binary",
                        "mimetype": "application/xml",
                    }
                )
                attachment.write({'res_model': 'account.move', 'res_id': move.id})
                move._message_log(
                    body=self.env._(
                        "%(ts)s: Payments for eRacun document (ElectroicId: %(eid)s) in the amount of %(mnt)s EUR has been reported successfully. (Request ID: %(req_id)s)",
                        ts=response['fiscalizationTimestamp'],
                        eid=move.l10n_hr_mer_document_eid,
                        mnt=amount_to_report,
                        req_id=response['fiscalizationRequestId'],
                    ),
                    attachment_ids=attachment.ids,
                )
                _mer_api_update_document_process_status(
                    move.company_id,
                    move.l10n_hr_mer_document_eid,
                    state_to_set,
                )
                move.l10n_hr_edi_addendum_id.business_document_status = state_to_set
