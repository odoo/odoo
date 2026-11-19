import base64

from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node
from odoo.tools.image import image_data_uri

from odoo.addons.l10n_gr_edi_delivery_note.utils import get_greek_vat_number, street_split

DELIVERY_NOTE_INVOICE_TYPE = '9.3'
GREECE_TIMEZONE = 'Europe/Athens'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _default_l10n_gr_edi_move_purpose(self):
        return '1' if self.env.company.account_fiscal_country_id.code == 'GR' else False

    is_greek_company = fields.Boolean(compute='_compute_is_greek_company')
    l10n_gr_edi_document_ids = fields.One2many(
        comodel_name='l10n_gr_edi.document',
        inverse_name='picking_id',
        copy=False,
        readonly=True,
    )
    l10n_gr_edi_state = fields.Selection(
        selection=[
            ('delivery_note_sent', "Delivery note sent"),
            ('delivery_note_error', "Delivery note send failed"),
        ],
        string="myDATA Status",
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
        tracking=True,
        copy=False,
    )
    l10n_gr_edi_mark = fields.Char(
        string="myDATA Mark",
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
        copy=False,
    )
    l10n_gr_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
        copy=False,
    )
    l10n_gr_edi_enable_send = fields.Boolean(compute='_compute_l10n_gr_edi_enable_send')
    l10n_gr_edi_alerts = fields.Json(compute='_compute_l10n_gr_edi_alerts')
    l10n_gr_edi_move_purpose = fields.Selection(
        selection=[
            ('1', "1 - Sale"),
            ('2', "2 - Sales on Behalf of Third Parties"),
            ('3', "3 - Sampling"),
            ('4', "4 - Exhibition"),
            ('5', "5 - Return"),
            ('6', "6 - Keeping"),
            ('7', "7 - Edit - Assembly"),
            ('8', "8 - Between Entity Branches"),
            ('9', "9 - Purchase"),
            ('10', "10 - Supply of ships and aircraft"),
            ('11', "11 - Free distribution"),
            ('12', "12 - Warranty"),
            ('13', "13 - Loan"),
            ('14', "14 - Storage by Third Party"),
            ('15', "15 - Return from Custody"),
            ('16', "16 - Recycling"),
            ('17', "17 - Destruction of waste material"),
            ('18', "18 - Fixed Asset Movement (Internal Circulation)"),
            ('19', "19 - Other Movements"),
        ],
        string="Move Purpose",
        default=_default_l10n_gr_edi_move_purpose,
    )
    l10n_gr_edi_other_move_purpose = fields.Char(string="Other Move Purpose")
    l10n_gr_edi_loading_address_street = fields.Char()
    l10n_gr_edi_loading_address_number = fields.Char()
    l10n_gr_edi_loading_address_zip = fields.Char()
    l10n_gr_edi_loading_address_city = fields.Char()
    l10n_gr_edi_delivery_address_street = fields.Char()
    l10n_gr_edi_delivery_address_number = fields.Char()
    l10n_gr_edi_delivery_address_zip = fields.Char()
    l10n_gr_edi_delivery_address_city = fields.Char()
    l10n_gr_edi_vehicle_number = fields.Char(string="myDATA Vehicle Number")

    ################################################################################
    # Compute methods
    ################################################################################

    @api.depends('company_id.account_fiscal_country_id.code')
    def _compute_is_greek_company(self):
        for picking in self:
            picking.is_greek_company = picking.company_id.account_fiscal_country_id.code == 'GR'

    @api.depends(
        'l10n_gr_edi_document_ids',
        'l10n_gr_edi_document_ids.state',
        'l10n_gr_edi_document_ids.mydata_mark',
        'l10n_gr_edi_document_ids.attachment_id',
    )
    def _compute_from_l10n_gr_edi_document_ids(self):
        for picking in self:
            documents = picking.l10n_gr_edi_document_ids.sorted()
            sent_document = documents.filtered(lambda document: document.state == 'delivery_note_sent')[:1]
            if sent_document:
                picking.l10n_gr_edi_state = 'delivery_note_sent'
                picking.l10n_gr_edi_mark = sent_document.mydata_mark
                picking.l10n_gr_edi_attachment_id = sent_document.attachment_id
            else:
                picking.l10n_gr_edi_state = 'delivery_note_error' if documents else False
                picking.l10n_gr_edi_mark = False
                picking.l10n_gr_edi_attachment_id = False

    @api.depends('is_greek_company', 'state', 'l10n_gr_edi_state')
    def _compute_l10n_gr_edi_enable_send(self):
        for picking in self:
            picking.l10n_gr_edi_enable_send = (
                picking.is_greek_company
                and picking.state == 'done'
                and picking.l10n_gr_edi_state != 'delivery_note_sent'
            )

    @api.depends('is_greek_company', 'state', 'l10n_gr_edi_state')
    def _compute_l10n_gr_edi_alerts(self):
        for picking in self:
            if picking.is_greek_company and picking.state == 'done' and picking.l10n_gr_edi_state != 'delivery_note_sent':
                picking.l10n_gr_edi_alerts = picking._origin._l10n_gr_edi_get_pre_error_dict() or False
            else:
                picking.l10n_gr_edi_alerts = False

    ################################################################################
    # Onchange methods
    ################################################################################

    @api.onchange('l10n_gr_edi_move_purpose')
    def _onchange_l10n_gr_edi_other_move_purpose(self):
        for picking in self:
            if picking.l10n_gr_edi_move_purpose != '19':
                picking.l10n_gr_edi_other_move_purpose = False

    @api.model
    def _l10n_gr_edi_get_loading_partner(self, picking_type, company):
        # The goods are loaded where they leave from the warehouse
        return picking_type.warehouse_id.partner_id or company.partner_id

    @api.onchange('is_greek_company', 'company_id', 'picking_type_id')
    def _onchange_l10n_gr_edi_loading_address(self):
        for picking in self:
            if picking.state == 'done':
                continue
            if picking.is_greek_company:
                loading_partner = self._l10n_gr_edi_get_loading_partner(picking.picking_type_id, picking.company_id)
                street_detail = street_split(loading_partner.street)
                picking.l10n_gr_edi_loading_address_street = street_detail['street_name']
                picking.l10n_gr_edi_loading_address_number = street_detail['street_number']
                picking.l10n_gr_edi_loading_address_zip = loading_partner.zip
                picking.l10n_gr_edi_loading_address_city = loading_partner.city
            else:
                picking.l10n_gr_edi_loading_address_street = False
                picking.l10n_gr_edi_loading_address_number = False
                picking.l10n_gr_edi_loading_address_zip = False
                picking.l10n_gr_edi_loading_address_city = False

    @api.onchange('is_greek_company', 'partner_id')
    def _onchange_l10n_gr_edi_delivery_address(self):
        for picking in self:
            if picking.state == 'done':
                continue
            if picking.is_greek_company:
                street_detail = street_split(picking.partner_id.street)
                picking.l10n_gr_edi_delivery_address_street = street_detail['street_name']
                picking.l10n_gr_edi_delivery_address_number = street_detail['street_number']
                picking.l10n_gr_edi_delivery_address_zip = picking.partner_id.zip
                picking.l10n_gr_edi_delivery_address_city = picking.partner_id.city
            else:
                picking.l10n_gr_edi_delivery_address_street = False
                picking.l10n_gr_edi_delivery_address_number = False
                picking.l10n_gr_edi_delivery_address_zip = False
                picking.l10n_gr_edi_delivery_address_city = False

    ################################################################################
    # myDATA XML
    ################################################################################

    def _l10n_gr_edi_get_series_and_aa(self):
        """Split the transfer name in a myDATA series and serial number (aa).
        e.g. 'WH/OUT/00012' -> ('WH_OUT', '00012')
        """
        self.ensure_one()
        *series, aa = (self.name or '').split('/')
        return '_'.join(series), aa

    def _l10n_gr_edi_get_issue_and_dispatch_datetimes(self, issue_datetime=None):
        """Return the issue and dispatch datetimes of the delivery note, in the Greek timezone.

        myDATA requires the issue date to be the current date and the dispatch date to be today
        or later. The delivery note is thus issued when it is sent, and the goods are dispatched
        when the transfer was validated, or when the delivery note is issued if it is sent later.

        :param datetime issue_datetime: UTC issuance datetime, now by default.
        :return: (issue_datetime, dispatch_datetime), both timezone-aware
        """
        self.ensure_one()
        greek_self = self.with_context(tz=GREECE_TIMEZONE)
        issue = fields.Datetime.context_timestamp(greek_self, issue_datetime or fields.Datetime.now())
        validation = fields.Datetime.context_timestamp(greek_self, self.date_done) if self.date_done else issue
        dispatch = validation if validation.date() >= issue.date() else issue
        return issue, dispatch

    def _l10n_gr_edi_get_delivery_note_xml_vals(self, issue_datetime=None):
        """Values used to render the ``l10n_gr_edi_delivery_note.mydata_delivery_note`` template.

        A delivery note only tracks physical goods: every amount is 0 and the VAT category is 8
        (records without VAT).

        :param datetime issue_datetime: UTC issuance datetime, now by default.
        """
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id.commercial_partner_id
        issuer_street = street_split(company.street)
        counterpart_street = street_split(partner.street)
        series, aa = self._l10n_gr_edi_get_series_and_aa()
        issue_date, dispatch_date = self._l10n_gr_edi_get_issue_and_dispatch_datetimes(issue_datetime)
        zero_classification = [{'category': 'category3', 'amount': 0}]

        details = []
        for line_number, move in enumerate(self.move_ids.filtered(lambda move: move.state == 'done'), start=1):
            details.append({
                'line_number': line_number,
                'item_description': (move.product_id.display_name or '')[:300],
                'quantity': move.quantity,
                'unit_of_measure': move.l10n_gr_edi_measurement_unit,
                'net_value': 0,
                'vat_category': 8,
                'vat_amount': 0,
                'icls': zero_classification,
            })

        return {
            'issuer_vat_number': get_greek_vat_number(company.vat),
            'issuer_country': company.country_code,
            'issuer_branch': company.l10n_gr_edi_branch_number or 0,
            'issuer_name': company.name,
            'issuer_street': issuer_street['street_name'],
            'issuer_number': issuer_street['street_number'],
            'issuer_postal_code': company.zip,
            'issuer_city': company.city,
            'counterpart_vat': get_greek_vat_number(partner.vat),
            'counterpart_country': partner.country_code,
            'counterpart_branch': partner.l10n_gr_edi_branch_number or 0,
            'counterpart_name': partner.name,
            'counterpart_street': counterpart_street['street_name'],
            'counterpart_number': counterpart_street['street_number'],
            'counterpart_postal_code': partner.zip,
            'counterpart_city': partner.city,
            'header_series': series,
            'header_aa': aa,
            'header_issue_date': issue_date.strftime('%Y-%m-%d'),
            'header_invoice_type': DELIVERY_NOTE_INVOICE_TYPE,
            'header_dispatch_date': dispatch_date.strftime('%Y-%m-%d'),
            'header_dispatch_time': dispatch_date.strftime('%H:%M:%S'),
            'header_vehicle_number': self.l10n_gr_edi_vehicle_number,
            'header_move_purpose': self.l10n_gr_edi_move_purpose,
            'header_other_move_purpose_title': self.l10n_gr_edi_other_move_purpose if self.l10n_gr_edi_move_purpose == '19' else False,
            'loading_street': self.l10n_gr_edi_loading_address_street,
            'loading_number': self.l10n_gr_edi_loading_address_number,
            'loading_postal_code': self.l10n_gr_edi_loading_address_zip,
            'loading_city': self.l10n_gr_edi_loading_address_city,
            'delivery_street': self.l10n_gr_edi_delivery_address_street,
            'delivery_number': self.l10n_gr_edi_delivery_address_number,
            'delivery_postal_code': self.l10n_gr_edi_delivery_address_zip,
            'delivery_city': self.l10n_gr_edi_delivery_address_city,
            'details': details,
            'summary_icls': zero_classification,
        }

    def _l10n_gr_edi_generate_delivery_note_xml(self, issue_datetime=None):
        """Render the myDATA delivery note XML, as UTF-8 bytes.

        :param datetime issue_datetime: UTC issuance datetime, now by default.
        """
        self.ensure_one()
        xml_content = self.env['ir.qweb']._render(
            'l10n_gr_edi_delivery_note.mydata_delivery_note',
            self._l10n_gr_edi_get_delivery_note_xml_vals(issue_datetime),
        )
        return etree.tostring(cleanup_xml_node(xml_content), encoding='UTF-8', xml_declaration=True, standalone=True)

    ################################################################################
    # Checks
    ################################################################################

    def _l10n_gr_edi_get_pre_error_dict(self):
        """
        Try to catch all possible errors before sending to myDATA.
        Returns an error dictionary in the format of Actionable Error JSON.
        """
        self.ensure_one()
        errors = {}
        company = self.company_id
        partner = self.partner_id.commercial_partner_id

        company_view = self.env.ref('l10n_gr_edi_delivery_note.view_company_form_inherit_mydata_required_fields')
        partner_view = self.env.ref('l10n_gr_edi_delivery_note.view_partner_form_inherit_mydata_required_fields')
        error_action_company = {
            'action_text': self.env._("View Company"),
            'action': company._get_records_action(name=self.env._("Company"), views=[(company_view.id, 'form')]),
        }
        error_action_partner = {
            'action_text': self.env._("View Partner"),
            'action': partner._get_records_action(name=self.env._("Partner"), views=[(partner_view.id, 'form')]),
        }
        error_action_gr_settings = {
            'action_text': self.env._("View Settings"),
            'action': {
                'name': self.env._("Settings"),
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': '/odoo/settings#l10n_gr_edi_aade_settings',
            },
        }

        if self.state != 'done':
            errors['l10n_gr_edi_picking_not_done'] = {
                'message': self.env._("You can only send a validated transfer to myDATA."),
            }
        if not (company.l10n_gr_edi_aade_id and company.l10n_gr_edi_aade_key):
            errors['l10n_gr_edi_company_no_cred'] = {
                'message': self.env._("You need to set AADE ID and Key in the company settings."),
                **error_action_gr_settings,
            }
        if not company.vat:
            errors['l10n_gr_edi_company_no_vat'] = {
                'message': self.env._("Missing VAT on company %s.", company.name),
                **error_action_company,
            }
        if not (company.zip and company.city):
            errors['l10n_gr_edi_company_no_zip_city'] = {
                'message': self.env._("Missing city and/or ZIP code on company %s.", company.name),
                **error_action_company,
            }
        company_street = street_split(company.street)
        if not (company_street['street_name'] and company_street['street_number']):
            errors['l10n_gr_edi_company_no_street'] = {
                'message': self.env._("Missing street and/or street number on company %s.", company.name),
                **error_action_company,
            }

        if not partner:
            errors['l10n_gr_edi_no_partner'] = {
                'message': self.env._("A contact must be set on the transfer to send it to myDATA."),
            }
        else:
            if not partner.vat:
                errors['l10n_gr_edi_partner_no_vat'] = {
                    'message': self.env._("Missing VAT on partner %s.", partner.name),
                    **error_action_partner,
                }
            if not (partner.zip and partner.city):
                errors['l10n_gr_edi_partner_no_zip_city'] = {
                    'message': self.env._("Missing city and/or ZIP code on partner %s.", partner.name),
                    **error_action_partner,
                }
            partner_street = street_split(partner.street)
            if not (partner_street['street_name'] and partner_street['street_number']):
                errors['l10n_gr_edi_partner_no_street'] = {
                    'message': self.env._("Missing street and/or street number on partner %s.", partner.name),
                    **error_action_partner,
                }

        _series, aa = self._l10n_gr_edi_get_series_and_aa()
        if not aa.isdigit():
            errors['l10n_gr_edi_invalid_aa'] = {
                'message': self.env._(
                    "The reference of %s must end with a number (e.g. WH/OUT/00012) to be sent to myDATA.",
                    self.name,
                ),
            }
        if not self.l10n_gr_edi_move_purpose:
            errors['l10n_gr_edi_no_move_purpose'] = {
                'message': self.env._("Missing myDATA move purpose."),
            }
        elif self.l10n_gr_edi_move_purpose == '19' and not self.l10n_gr_edi_other_move_purpose:
            errors['l10n_gr_edi_no_other_move_purpose'] = {
                'message': self.env._("Missing the description of the other move purpose."),
            }
        loading_address = (
            self.l10n_gr_edi_loading_address_street,
            self.l10n_gr_edi_loading_address_number,
            self.l10n_gr_edi_loading_address_zip,
            self.l10n_gr_edi_loading_address_city,
        )
        if not all(loading_address):
            errors['l10n_gr_edi_no_loading_address'] = {
                'message': self.env._("The myDATA loading address is incomplete."),
            }
        delivery_address = (
            self.l10n_gr_edi_delivery_address_street,
            self.l10n_gr_edi_delivery_address_number,
            self.l10n_gr_edi_delivery_address_zip,
            self.l10n_gr_edi_delivery_address_city,
        )
        if not all(delivery_address):
            errors['l10n_gr_edi_no_delivery_address'] = {
                'message': self.env._("The myDATA delivery address is incomplete."),
            }

        done_moves = self.move_ids.filtered(lambda move: move.state == 'done')
        for line_number, move in enumerate(done_moves, start=1):
            if not move.l10n_gr_edi_measurement_unit:
                errors[f'l10n_gr_edi_{line_number}_missing_uom'] = {
                    'message': self.env._(
                        "The unit of measure on line %s is not supported by myDATA. "
                        "Please use one of 'Units', 'kg', 'L', 'm', 'm²' or 'm³'.",
                        line_number,
                    ),
                }
        return errors

    ################################################################################
    # Report
    ################################################################################

    def _l10n_gr_edi_get_sent_document(self):
        self.ensure_one()
        return self.l10n_gr_edi_document_ids.filtered(lambda document: document.state == 'delivery_note_sent').sorted()[:1]

    def _l10n_gr_edi_get_extra_invoice_report_values(self):
        """Values displayed on the delivery slip once the delivery note is issued."""
        self.ensure_one()
        document = self._l10n_gr_edi_get_sent_document()
        if not document:
            return {}

        values = {'mydata_mark': document.mydata_mark}
        if document.mydata_url:
            values['barcode_src'] = image_data_uri(base64.b64encode(
                self.env['ir.actions.report'].barcode(
                    barcode_type='QR',
                    value=document.mydata_url,
                    width=180,
                    height=180,
                    quiet=0,
                )
            ))
        return values

    ################################################################################
    # Send logic
    ################################################################################

    def _l10n_gr_edi_send_delivery_note(self):
        """Transmit the delivery note to myDATA. Implemented in l10n_gr_edi_delivery_note_e_invoo."""
        raise UserError(self.env._("No myDATA provider is available to send delivery notes."))

    def action_l10n_gr_edi_try_send_delivery_note(self):
        self.ensure_one()
        if not self.l10n_gr_edi_enable_send:
            raise UserError(self.env._("This transfer cannot be sent to myDATA."))
        if errors := self._l10n_gr_edi_get_pre_error_dict():
            raise UserError('\n'.join(error['message'] for error in errors.values()))
        self._l10n_gr_edi_send_delivery_note()
