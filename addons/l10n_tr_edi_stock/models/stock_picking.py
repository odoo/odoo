import uuid
from io import BytesIO

from lxml import etree

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import cleanup_xml_node
from odoo.tools.xml_utils import find_xml_value

from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES
from odoo.addons.l10n_tr_edi_stock.const import (
    DOCUMENT_STATE_TO_DISPATCH_STATUS,
    DOCUMENT_STATE_TO_RESPONSE_STATUS,
    RESPONSE_SETTLED_STATUSES,
)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_tr_edi_uuid = fields.Char(
        string="E-Document UUID",
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
    )
    l10n_tr_edi_document_ids = fields.One2many(
        comodel_name='l10n_tr_edi.document',
        inverse_name='picking_id',
        copy=False,
        readonly=True,
    )
    l10n_tr_edi_send_status = fields.Selection(
        string="E-Document Status",
        selection=[
            ('error', "Error"),
            ('not_sent', "Not sent"),
            ('sent', "Sent and waiting response"),
            ('succeed', "Successful"),
            ('waiting', "Waiting"),
            ('unknown', "Unknown"),
        ],
        compute='_compute_l10n_tr_edi_send_status',
        store=True,
        copy=False,
        readonly=True,
        init_storage=lambda model: model.env.cr.execute(
            "UPDATE stock_picking SET l10n_tr_edi_send_status = 'not_sent' WHERE l10n_tr_edi_send_status IS NULL",
        ),
    )
    l10n_tr_edi_response_status = fields.Selection(
        string="e-Dispatch Response Status",
        selection=[
            ('not_sent', "Not sent"),
            ('sent', "Response Sent"),
            ('unknown', "Response Unknown"),
            ('waiting', "Response Waiting"),
            ('error', "Response Error"),
            ('accepted', "Response Accepted"),
            ('accepted_automatically', "Response Accepted Automatically"),
            ('rejected', "Response Rejected"),
        ],
        compute='_compute_l10n_tr_edi_response_status',
        store=True,
        readonly=True,
        copy=False,
        init_storage=lambda model: model.env.cr.execute(
            "UPDATE stock_picking SET l10n_tr_edi_response_status = 'not_sent' WHERE l10n_tr_edi_response_status IS NULL",
        ),
    )
    l10n_tr_edi_response_xml_file = fields.Binary(
        string="Response XML File",
        copy=False,
        attachment=True,
    )
    l10n_tr_edi_response_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Response XML",
        store=True,
        compute=lambda self: self._compute_linked_attachment_id('l10n_tr_edi_response_xml_id', 'l10n_tr_edi_response_xml_file'),
        depends=['l10n_tr_edi_response_xml_file'],
    )
    l10n_tr_edi_dispatch_type = fields.Selection(
        string="Dispatch Handling",
        help="Used to populate the type of dispatch. 'Invoice Serves as e-Dispatch' is only applicable for e-Archive Customers.",
        selection=[
            ('SEVK', "Online"),
            ('MATBUDAN', "Pre-printed"),
            ('IS_DESPATCH', "Invoice Serves as e-Dispatch"),
        ],
        default='SEVK',
        tracking=True,
        copy=False,
    )
    l10n_tr_edi_carrier_id = fields.Many2one(
        string="Carrier (TR)",
        help="Used when the dispatch is made through a third-party carrier company. Populating this makes the Vehicle Plate and Drivers optional.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_edi_buyer_id = fields.Many2one(
        string="Buyer",
        help="Used for the original party who purchases the good when the Delivery Address is for another recipient",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_edi_seller_supplier_id = fields.Many2one(
        string="Seller Supplier",
        help="Used for the information of the supplier of the goods in the delivery note.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_edi_buyer_originator_id = fields.Many2one(
        string="Buyer Originator",
        help="Used for the original initiator of the goods acquisition and requesting process.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_edi_delivery_printed_number = fields.Char(string="Printed Delivery Note Number", copy=False)
    l10n_tr_edi_delivery_date = fields.Date(string="Printed Delivery Note Date", copy=False)
    l10n_tr_vehicle_plate = fields.Many2one(
        string="Vehicle Plate",
        help="Used to input the plate number of the truck.",
        comodel_name='l10n_tr_edi.vehicle.plate',
        domain="[('plate_number_type', '=', 'vehicle')]",
        copy=False,
    )
    l10n_tr_edi_trailer_plate_ids = fields.Many2many(
        string="Trailer Plates",
        help="Used to input the plate numbers of the trailers attached to the truck.",
        comodel_name='l10n_tr_edi.vehicle.plate',
        domain="[('plate_number_type', '=', 'trailer')]",
        relation='l10n_tr_edi_delivery_vehicle_rel',
        copy=False,
    )
    l10n_tr_edi_driver_ids = fields.Many2many(
        string="Drivers",
        help="Used for the individuals driving the truck.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_edi_delivery_notes = fields.Char(string="Delivery Notes", copy=False)
    l10n_tr_edi_edispatch_warnings = fields.Json(compute='_compute_l10n_tr_edi_edispatch_warnings')
    l10n_tr_edi_dispatch_enabled = fields.Boolean(compute='_compute_l10n_tr_edi_dispatch_enabled')
    l10n_tr_edi_edispatch_xml_file = fields.Binary(
        string="e-Dispatch XML File",
        copy=False,
        attachment=True,
    )
    l10n_tr_edi_edispatch_xml_id = fields.Many2one(
        "ir.attachment",
        store=True,
        readonly=False,
        string="e-Dispatch XML",
        compute=lambda self: self._compute_linked_attachment_id('l10n_tr_edi_edispatch_xml_id', 'l10n_tr_edi_edispatch_xml_file'),
        depends=['l10n_tr_edi_edispatch_xml_file'],
    )

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        """Helper to retrieve Attachment from Binary fields
        This is needed because fields.Many2one('ir.attachment') makes all
        attachments available to the user.
        """
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('res_field', '=', binary_field),
        ])
        picking_vals = attachments.grouped('res_id')
        for picking in self:
            picking[attachment_field] = picking_vals.get(picking._origin.id, False)

    def write(self, vals):
        if 'l10n_tr_edi_edispatch_xml_id' not in vals:
            return super().write(vals)

        # E-Receipt flow: user has to manually pick an attachment (not ideal UX).
        # This would fit better with Documents, but thats Enterprise-only,
        # so we handle it ourselves in Community.
        #
        # Problem: changing `l10n_tr_edi_edispatch_xml_id` doesnt update
        # the attachments `res_model` / `res_id`. Attachments keep pointing
        # to whatever they were linked to before.
        #
        # So we fix it manually:
        # - detach the old attachment
        # - link the new one to this record
        new_attachment = self.env['ir.attachment'].browse(vals.get('l10n_tr_edi_edispatch_xml_id'))
        old_attachment = self.l10n_tr_edi_edispatch_xml_id
        res = super().write(vals)

        old_attachment.res_model, old_attachment.res_id = False, False
        new_attachment.res_model, new_attachment.res_id = self._name, self.id
        self.invalidate_recordset(['l10n_tr_edi_edispatch_xml_id', 'l10n_tr_edi_edispatch_xml_file'])

        return res

    @api.depends('l10n_tr_edi_document_ids.state', 'l10n_tr_edi_document_ids.document_type')
    def _compute_l10n_tr_edi_send_status(self):
        for picking in self:
            document = picking.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type == 'edispatch')[:1]
            picking.l10n_tr_edi_send_status = DOCUMENT_STATE_TO_DISPATCH_STATUS.get(document.state, 'not_sent')

    @api.depends('l10n_tr_edi_document_ids.state', 'l10n_tr_edi_document_ids.message', 'l10n_tr_edi_document_ids.document_type')
    def _compute_l10n_tr_edi_response_status(self):
        for picking in self:
            document = picking.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type == 'edispatch_response')[:1]
            if not document:
                picking.l10n_tr_edi_response_status = 'not_sent'
            elif document.message and document.state in {'sent', 'waiting'}:
                # The answer couldn't be followed up with the provider: it can be sent again.
                picking.l10n_tr_edi_response_status = 'error'
            else:
                picking.l10n_tr_edi_response_status = DOCUMENT_STATE_TO_RESPONSE_STATUS.get(document.state, 'not_sent')

    @api.depends('company_id.l10n_tr_edi_provider')
    def _compute_l10n_tr_edi_dispatch_enabled(self):
        for picking in self:
            picking.l10n_tr_edi_dispatch_enabled = bool(picking.company_id) and picking.company_id._l10n_tr_edi_dispatch_enabled()

    @api.depends(
        'l10n_tr_edi_carrier_id', 'l10n_tr_edi_buyer_id', 'l10n_tr_edi_seller_supplier_id',
        'l10n_tr_edi_buyer_originator_id', 'l10n_tr_edi_delivery_printed_number',
        'l10n_tr_edi_delivery_date', 'l10n_tr_vehicle_plate', 'l10n_tr_edi_trailer_plate_ids',
        'l10n_tr_edi_driver_ids', 'partner_id',
    )
    def _compute_l10n_tr_edi_edispatch_warnings(self):
        for picking in self:
            if (
                picking.country_code == "TR"
                and picking.picking_type_code == "outgoing"
                and picking.state in {"assigned", "done"}
            ):
                picking.l10n_tr_edi_edispatch_warnings = picking._l10n_tr_validate_edispatch_fields()
            else:
                picking.l10n_tr_edi_edispatch_warnings = False

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if picking.country_code != 'TR' or picking.picking_type_code != 'outgoing' or picking.state != 'done':
                continue
            elif not picking.partner_id:
                picking.message_post(
                    body=_("e-Dispatch will not be generated as the Delivery Address is not set.")
                )
        return res

    def _l10n_tr_validate_edispatch_on_done(self):
        partners = (
            self.partner_id
            | self.l10n_tr_edi_buyer_id
            | self.l10n_tr_edi_seller_supplier_id
            | self.l10n_tr_edi_buyer_originator_id
        )
        partners_requiring_tax_office = (
            self.company_id.partner_id
            | self.partner_id.commercial_partner_id
            | self.l10n_tr_edi_carrier_id
        ).filtered(lambda p: p.l10n_tr_edi_customer_status == 'einvoice')

        error_messages = (
            partners._l10n_tr_edi_validate_partner_details() |
            partners_requiring_tax_office._l10n_tr_edi_validate_partner_details(tax_office_required=True)
        )

        if self.l10n_tr_edi_dispatch_type == 'MATBUDAN':
            if not self.l10n_tr_edi_delivery_date:
                error_messages['invalid_matbudan_date'] = {
                    'message': _("Printed Delivery Note Date is required."),
                    'level': 'danger',
                }
            if (
                not self.l10n_tr_edi_delivery_printed_number
                or len(self.l10n_tr_edi_delivery_printed_number) != 16
            ):
                error_messages['invalid_matbudan_number'] = {
                    'message': _("Printed Delivery Note Number of 16 characters is required."),
                    'level': 'danger',
                }

        invalid_country_drivers = self.l10n_tr_edi_driver_ids.filtered(
            lambda driver: not driver.country_id or driver.country_id.code != 'TR'
        )
        invalid_tckn_drivers = (self.l10n_tr_edi_driver_ids - invalid_country_drivers).filtered(
            lambda driver: not driver.vat or (driver.vat and len(driver.vat) != 11)
        )

        if drivers := len(invalid_country_drivers):
            error_messages['invalid_driver_country'] = {
                'message': _(
                    "Only Drivers from Türkiye are valid. Please update the Country and enter a valid TCKN in the Tax ID.",
                ),
                'action_text': _(
                    "View %s",
                    (drivers == 1 and invalid_country_drivers.name) or _("Drivers"),
                ),
                'action': invalid_country_drivers._get_records_action(
                    name=_("Drivers"),
                ),
                'level': 'danger',
            }
        if drivers := len(invalid_tckn_drivers):
            driver_placeholder = drivers > 1 and _("Drivers") or _("%s's", invalid_tckn_drivers.name)
            error_messages['invalid_driver_tckn'] = {
                'message': _("%s TCKN is required.", driver_placeholder),
                'action_text': _("View %s", drivers == 1 and invalid_tckn_drivers.name or _("Drivers")),
                'action': invalid_tckn_drivers._get_records_action(name=_("Drivers")),
                'level': 'danger',
            }

        if self.l10n_tr_edi_dispatch_type == 'IS_DESPATCH':
            return error_messages or False

        if (
            not self.l10n_tr_edi_carrier_id
            and not self.l10n_tr_edi_driver_ids
            and not self.l10n_tr_vehicle_plate
        ):
            error_messages['required_carrier_details'] = {
                'message': _("Carrier is required (optional when both the Driver and Vehicle Plate are filled)."),
                'level': 'danger',
            }

        elif not self.l10n_tr_edi_carrier_id and not self.l10n_tr_edi_driver_ids:
            error_messages['required_driver_details'] = {
                'message': _("At least one Driver is required."),
                'level': 'danger',
            }

        elif not self.l10n_tr_edi_carrier_id and not self.l10n_tr_vehicle_plate:
            error_messages['required_vehicle_details'] = {
                'message': _("Vehicle Plate is required."),
                'level': 'danger',
            }

        return error_messages or False

    def _l10n_tr_validate_edispatch_fields(self):
        self.ensure_one()
        if self.state not in {'assigned', 'done'}:
            return {
                'invalid_transfer_state': {
                    'message': _("Please validate the transfer first to generate the XML"),
                }
            }
        if not self.partner_id:
            return {
                'missing_delivery_partner_id': {
                    'message': _("e-Dispatch will not be generated as the Delivery Address is not set."),
                }
            }
        if self.state == 'done':
            return self._l10n_tr_validate_edispatch_on_done()

    def action_l10n_tr_edi_send_edispatch_xml(self):
        if self.l10n_tr_edi_edispatch_warnings:
            raise UserError(_("Cannot send the XML when there are warnings."))
        self._l10n_tr_generate_edispatch_xml()
        xml_file = BytesIO(self.l10n_tr_edi_edispatch_xml_id.raw or b'')
        xml_file.name = self.l10n_tr_edi_edispatch_xml_id.name or ''
        self._l10n_tr_edi_send_document(xml_file)

    def _l10n_tr_edi_send_document(self, xml_file):
        """Send the e-Dispatch XML through the company's e-Document provider, raising on failure.

        Unlike invoices, no error e-Document is recorded: the error reaches the user, and the dispatch stays
        unsent so it can be corrected and sent again. Provider modules override this when the company uses them.

        :param xml_file: the e-Dispatch XML, as a named file-like object.
        """
        self.ensure_one()
        raise UserError(self.env._("No e-Document provider is set on %s.", self.company_id.display_name))

    def _l10n_tr_edi_get_provider(self):
        """Return the provider this transfer's e-Dispatch was sent through, or the company's provider when
        the transfer has no e-Dispatch yet."""
        self.ensure_one()
        if document := self.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type == 'edispatch')[:1]:
            return document.provider
        return self.company_id.l10n_tr_edi_provider

    def action_l10n_tr_edi_fetch_status(self):
        self._l10n_tr_edi_fetch_status()

    def _l10n_tr_edi_fetch_status(self):
        """Update the GİB state of these transfers' e-Dispatches from the provider each one was sent through."""
        for provider, pickings in self.grouped(lambda picking: picking._l10n_tr_edi_get_provider()).items():
            pickings._l10n_tr_edi_fetch_status_documents(provider)

    def _l10n_tr_edi_fetch_status_documents(self, provider):
        """Update the e-Dispatch state of these transfers, all sent through `provider`.

        Provider modules override this for the documents they hold. Without a provider there is
        nobody to ask, so nothing is updated.

        :param provider: the provider the transfers' e-Dispatches were sent through.
        """

    def _l10n_tr_edi_fetch_dispatches(self):
        """Import the received e-Dispatches not yet in Odoo, for each Turkish company from its provider."""
        for company in self.env.companies:
            if company.country_code == 'TR' and company.l10n_tr_edi_provider:
                self.with_company(company)._l10n_tr_edi_fetch_provider_dispatches(company.l10n_tr_edi_provider)

    def _l10n_tr_edi_fetch_provider_dispatches(self, provider):
        """Import the received e-Dispatches not yet in Odoo from `provider`, for the current company.

        Provider modules override this for their own provider, storing each received XML with
        `_l10n_tr_edi_store_received_dispatch`.

        :param provider: the e-Document provider of the current company.
        """

    @api.model
    def _l10n_tr_edi_store_received_dispatch(self, xml_content):
        """Store a received e-Dispatch XML as an attachment, to be linked to its receipt.

        :param xml_content: the e-Dispatch XML, as bytes.
        :return: the created attachment.
        """
        tree = etree.fromstring(xml_content)
        document_id = self._l10n_tr_edi_get_tag_text('./cbc:ID', tree)
        supplier_name = self._l10n_tr_edi_get_tag_text('.//cac:DespatchSupplierParty/cac:Party/cac:PartyName/cbc:Name', tree)

        return self.env['ir.attachment'].create({
            'name': '%s_e_Dispatch.xml' % document_id,
            'description': supplier_name,
            'raw': xml_content,
            'type': 'binary',
            'mimetype': 'application/xml',
            'res_field': 'l10n_tr_edi_edispatch_xml_file',
        })

    def _l10n_tr_edi_set_document_state(self, state, provider, message=None, name=None):
        """Record the GİB state of this transfer's e-Dispatch, creating the document if needed.

        A received e-Dispatch imported again on another transfer updates the document it already has. The document
        follows the transfer's UUID, which an update from a received XML can change. It also keeps the e-Dispatch
        XML and number, so they can be found on the e-Documents tab.

        :param state: the new `l10n_tr_edi.document` state.
        :param provider: the integrator that reported the state.
        :param message: the error or information that comes with the state, replacing the previous one.
        :param name: the number of a received e-Dispatch; a sent one is numbered from the transfer.
        :return: the updated or created document.
        """
        self.ensure_one()
        values = {'state': state, 'provider': provider, 'message': message, 'uuid': self.l10n_tr_edi_uuid}
        document = self.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type == 'edispatch')[:1]
        if not document and self.l10n_tr_edi_uuid:
            document = self.env['l10n_tr_edi.document'].search([
                ('company_id', '=', self.company_id.id),
                ('document_type', '=', 'edispatch'),
                ('uuid', '=', self.l10n_tr_edi_uuid),
            ], limit=1)
        if document and document.picking_id != self:
            # A twin found on another transfer stays as it is there.
            return document
        # What was exchanged is filed once: a later state never renames the e-Dispatch or swaps its XML,
        # unless the transfer was updated from another e-Dispatch.
        refile = document.uuid != self.l10n_tr_edi_uuid
        if (refile or not document.attachment_id) and self.l10n_tr_edi_edispatch_xml_id:
            values['attachment_id'] = self.l10n_tr_edi_edispatch_xml_id.id
        if refile or not document.name:
            if name:
                values['name'] = name
            elif self.picking_type_code == 'outgoing' and self.picking_type_id.l10n_tr_edi_gib_sequence_code:
                values['name'] = self._l10n_tr_edi_get_dispatch_number()
        if document:
            document.write(values)
            return document
        return self.env['l10n_tr_edi.document'].create({
            **values,
            'picking_id': self.id,
            'company_id': self.company_id.id,
            'document_type': 'edispatch',
        })

    def _l10n_tr_edi_get_response_document(self):
        """Return the e-Document of the answer (receipt advice) to this transfer's e-Dispatch."""
        self.ensure_one()
        return self.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type == 'edispatch_response')[:1]

    def _l10n_tr_edi_set_response_state(self, state, provider, message=None, name=None):
        """Record the GİB state of the answer to this transfer's e-Dispatch, creating its document if needed.

        The answer's own UUID is not known: it is followed through the e-Dispatch's UUID.

        :param state: the new `l10n_tr_edi.document` state.
        :param provider: the integrator that reported the state.
        :param message: a failure to follow the answer up with the provider, replacing the previous one; the
                        transfer reads an answer with a message as in error, so it can be sent again.
        :param name: the number of the answer, when known.
        :return: the updated or created document.
        """
        self.ensure_one()
        values = {'state': state, 'provider': provider, 'message': message}
        if name:
            values['name'] = name
        if document := self._l10n_tr_edi_get_response_document():
            document.write(values)
            return document
        return self.env['l10n_tr_edi.document'].create({
            **values,
            'picking_id': self.id,
            'company_id': self.company_id.id,
            'document_type': 'edispatch_response',
        })

    def _l10n_tr_edi_store_response_xml(self, xml_content):
        """Attach the signed XML of the answer to this transfer's e-Dispatch and link it to the answer's e-Document.

        :param xml_content: the answer XML, as bytes.
        :return: the created attachment.
        """
        self.ensure_one()
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}_e_Dispatch_Response.xml",
            'raw': xml_content,
            'res_model': 'stock.picking',
            'res_id': self.id,
            'res_field': 'l10n_tr_edi_response_xml_file',
            'type': 'binary',
            'mimetype': 'application/xml',
        })
        self._l10n_tr_edi_get_response_document().attachment_id = attachment
        self.invalidate_recordset(['l10n_tr_edi_response_xml_id', 'l10n_tr_edi_response_xml_file'])
        self._compute_linked_attachment_id('l10n_tr_edi_response_xml_id', 'l10n_tr_edi_response_xml_file')
        return attachment

    def action_l10n_tr_edi_fetch_response_status(self):
        self._l10n_tr_edi_fetch_response_status()

    def _l10n_tr_edi_fetch_response_status(self, from_cron=False):
        """Update the GİB state of the answers to these transfers' e-Dispatches, each from the provider holding it:
        the provider the answer went through, else the e-Dispatch's.

        :param from_cron: whether the scheduled action asks, rather than a user who is there to read why it failed.
        """
        for provider, pickings in self.grouped(
            lambda picking: picking._l10n_tr_edi_get_response_document().provider or picking._l10n_tr_edi_get_provider(),
        ).items():
            pickings._l10n_tr_edi_fetch_response_status_documents(provider, from_cron=from_cron)

    def _l10n_tr_edi_fetch_response_status_documents(self, provider, from_cron=False):
        """Update the state of the answers to these transfers' e-Dispatches, all held by `provider`.

        Provider modules override this for the answers they hold. Without a provider there is
        nobody to ask, so nothing is updated.

        :param provider: the provider holding the answers.
        :param from_cron: whether the scheduled action asks, rather than a user who is there to read why it failed.
        """

    @api.model
    def _l10n_tr_edi_get_response_status_domains(self, picking_type_code):
        """Return the domains of the transfers of `picking_type_code` whose e-Dispatch answer is still followed up:
        on a receipt, the answer given to the received e-Dispatch; on a delivery, the customer's answer to ours.

        Provider modules add what they still retrieve once the answer is settled.

        :param picking_type_code: 'incoming' or 'outgoing'.
        :return: a list of domains, any of which selects a transfer.
        """
        domain = Domain('picking_type_code', '=', picking_type_code) & Domain('l10n_tr_edi_uuid', '!=', False)
        if picking_type_code == 'incoming':
            return [domain & Domain('l10n_tr_edi_response_status', 'in', ('sent', 'waiting', 'error'))]
        return [
            domain
            & Domain('l10n_tr_edi_send_status', '=', 'succeed')
            & Domain('l10n_tr_edi_response_status', 'not in', RESPONSE_SETTLED_STATUSES),
        ]

    def _l10n_tr_edi_get_dispatch_number(self):
        """
        Returns the serial number for the e-Dispatch document in the format required by the GİB.
        The format is: '[Picking Type Code][Year (YYYY)][Sequence Number of 9 digits padded with 0]'
        Example: 'OUT2025123456789'
        """
        sequence_number = self.name.removeprefix(self.picking_type_id.sequence_id.prefix or '').removesuffix(self.picking_type_id.sequence_id.suffix or '')
        return f"{self.picking_type_id.l10n_tr_edi_gib_sequence_code.upper()}{self.scheduled_date.year}{sequence_number.zfill(9)}"

    def _l10n_tr_generate_edispatch_xml(self):
        drivers = []
        for driver in self.l10n_tr_edi_driver_ids:
            driver_name = driver.name.split(' ', 1)
            drivers.append({
                'name': driver_name[0],
                'fname': driver_name[1] if len(driver_name) > 1 else '\u200B',
                'tckn': driver.vat,
            })
        scheduled_date_local = fields.Datetime.context_timestamp(
            self.with_context(tz='Europe/Istanbul'),
            self.scheduled_date,
        )
        date_done_local = fields.Datetime.context_timestamp(
            self.with_context(tz='Europe/Istanbul'),
            self.date_done,
        )
        values = {
            'ubl_version_id': 2.1,
            'customization_id': 'TR1.2.1',
            'uuid': self.l10n_tr_edi_uuid,
            'id': self._l10n_tr_edi_get_dispatch_number(),
            'picking': self,
            'current_company': self.env.company.partner_id,
            'issue_date': scheduled_date_local.date().strftime('%Y-%m-%d'),
            'issue_time': scheduled_date_local.time().strftime('%H:%M:%S'),
            'actual_date': date_done_local.strftime('%Y-%m-%d'),
            'actual_time': date_done_local.strftime('%H:%M:%S'),
            'line_count': len(self.move_ids),
            'printed_date': self.l10n_tr_edi_delivery_date and self.l10n_tr_edi_delivery_date.strftime('%Y-%m-%d'),
            'drivers': drivers,
            'default_tckn': '22222222222',
            'dispatch_scenario': 'TEMELIRSALIYE',
            'copy_indicator': 'false',
        }
        xml_content = self.env['ir.qweb']._render(
            'l10n_tr_edi_stock.l10n_tr_edispatch_format',
            values
        )
        xml_string = etree.tostring(
            cleanup_xml_node(xml_content),
            pretty_print=False,
            encoding='UTF-8',
        )
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}_e_Dispatch.xml",
            'raw': xml_string,
            'res_model': self._name,
            'res_id': self.id,
            'res_field': 'l10n_tr_edi_edispatch_xml_file',
            'mimetype': 'application/xml',
        })
        self.invalidate_recordset(fnames=['l10n_tr_edi_edispatch_xml_id', 'l10n_tr_edi_edispatch_xml_file'])
        # Has to be manually tiggered since the field is stored and the update on l10n_tr_edi_edispatch_xml_file
        # Does not happen even when the file changes
        self._compute_linked_attachment_id('l10n_tr_edi_edispatch_xml_id', 'l10n_tr_edi_edispatch_xml_file')
        self.message_post(
            body=_("e-Dispatch XML file generated successfully."),
            attachment_ids=[attachment.id],
            subtype_xmlid='mail.mt_note',
        )

    def action_l10n_tr_edi_generate_edispatch_xml(self, is_list=False):
        invalid_picking_names = []
        for picking in self:
            if picking.country_code == 'TR' and picking.picking_type_code == 'outgoing':
                if picking._l10n_tr_validate_edispatch_fields():
                    invalid_picking_names.append(picking.name)
                else:
                    picking._l10n_tr_generate_edispatch_xml()
        if is_list and invalid_picking_names:
            raise UserError(_("Error occurred in generating XML for following records:\n- %s", '\n- '.join(invalid_picking_names)))

    def _get_mail_thread_data_attachments(self):
        # EXTENDS 'stock'
        # Else, attachments with 'res_field' get excluded.
        return (
            super()._get_mail_thread_data_attachments()
            + self.l10n_tr_edi_edispatch_xml_id
            + self.l10n_tr_edi_response_xml_id
        )

    def _l10n_tr_edi_get_tag_text(self, xpath, tree, default=''):
        return find_xml_value(xpath, tree, UBL_NAMESPACES) or default

    def _l10n_tr_edi_get_partner_vals_from_xml(self, tree, xpath):
        party = tree.find(xpath, namespaces=UBL_NAMESPACES)
        if party is None:
            return
        return {
            'name': self._l10n_tr_edi_get_tag_text('./cac:PartyName/cbc:Name', party) or
                    f"{self._l10n_tr_edi_get_tag_text('./cac:Person/cbc:FirstName', party)} {self._l10n_tr_edi_get_tag_text('./cac:Person/cbc:FamilyName', party)}",
            'vat': self._l10n_tr_edi_get_tag_text('./cac:PartyIdentification/cbc:ID[@schemeID="VKN" or @schemeID="TCKN"]', party),
            'street': self._l10n_tr_edi_get_tag_text('./cac:PostalAddress/cbc:StreetName', party),
            'city': self._l10n_tr_edi_get_tag_text('./cac:PostalAddress/cbc:CitySubdivisionName', party),
            'zip': self._l10n_tr_edi_get_tag_text('./cac:PostalAddress/cbc:PostalZone', party),
            'state': self._l10n_tr_edi_get_tag_text('./cac:PostalAddress/cbc:CityName', party),
            'country': self._l10n_tr_edi_get_tag_text('./cac:PostalAddress/cac:Country/cbc:Name', party),
            'phone': self._l10n_tr_edi_get_tag_text('./cac:Contact/cbc:Telephone', party),
            'email': self._l10n_tr_edi_get_tag_text('./cac:Contact/cbc:ElectronicMail', party),
        }

    def _l10n_tr_edi_create_partner_from_xml(self, partner_vals):
        if (state := partner_vals.pop('state', None)) and (
            state_id := self.env['res.country.state'].search([('name', '=', state)], limit=1)
        ):
            partner_vals.pop('country')
            partner_vals.update({
                'state_id': state_id.id,
                'country_id': state_id.country_id.id,
                'code': state_id.country_id.code
            })
        elif (country := partner_vals.pop('country', None)) and (
            country_id := self.env['res.country'].with_context(lang='tr_TR').search([('name', '=', country)], limit=1)
        ):
            partner_vals.update({'country_id': country_id.id, 'code': country_id.code})

        if (code := partner_vals.pop('code', None)) and code != 'TR':
            partner_vals['l10n_tr_edi_edispatch_customs_zip'] = partner_vals.pop('zip', '')

        partner = self.env['res.partner'].with_context(no_vat_validation=True).create(partner_vals)
        return partner.id

    def _l10n_tr_edi_find_or_create_products_from_xml(self, receipt_lines):
        product_names = [
            self._l10n_tr_edi_get_tag_text('./cac:Item/cbc:Name', receipt) for receipt in receipt_lines
        ]
        existing_products = dict(self.env['product.product']._read_group(
            [('name', 'in', product_names)], ['name'], ['id:min'],
        ))

        products_to_create = []
        for receipt in receipt_lines:
            name = self._l10n_tr_edi_get_tag_text('./cac:Item/cbc:Name', receipt)
            if name not in existing_products:
                unece_code = receipt.find('./cbc:DeliveredQuantity', namespaces=UBL_NAMESPACES).get('unitCode', '')
                products_to_create.append({
                    'name': name,
                    'default_code': self._l10n_tr_edi_get_tag_text('./cac:Item/cac:SellersItemIdentification/cbc:ID', receipt),
                    'uom_id': self.env['uom.uom']._get_uom_from_unece_code(unece_code).id,
                })

        if products_to_create:
            created_products = self.env['product.product'].create(products_to_create)
            existing_products.update({product.name: product.id for product in created_products})

        return existing_products

    def _l10n_tr_edi_import_receipt_lines(self, tree):
        receipt_lines = tree.findall('./cac:DespatchLine', namespaces=UBL_NAMESPACES)
        if not receipt_lines:
            return []

        products_dict = self._l10n_tr_edi_find_or_create_products_from_xml(receipt_lines)
        source_location = self.picking_type_id.default_location_src_id

        values = []
        for receipt in receipt_lines:
            name = self._l10n_tr_edi_get_tag_text('./cac:Item/cbc:Name', receipt)
            values.append({
                'description_picking': name,
                'product_id': products_dict[name],
                'product_uom_qty': self._l10n_tr_edi_get_tag_text('./cbc:DeliveredQuantity', receipt),
                'picking_id': self.id,
                'location_dest_id': self.location_dest_id.id,
                'location_id': source_location.id,
            })
        return values

    def _l10n_tr_edi_import_vehicle_plate(self, tree):
        vehicle_plate = self._l10n_tr_edi_get_tag_text('.//cac:RoadTransport/cbc:LicensePlateID', tree)
        if not vehicle_plate:
            return
        vehicle_plate_id = self.env['l10n_tr_edi.vehicle.plate'].search_fetch(
            [('name', '=', vehicle_plate), ('plate_number_type', '=', 'vehicle')], ['id'], limit=1,
        )
        if not vehicle_plate_id:
            vehicle_plate_id = self.env['l10n_tr_edi.vehicle.plate'].create({
                'name': vehicle_plate,
                'plate_number_type': 'vehicle',
            })
        return vehicle_plate_id.id

    def _l10n_tr_edi_import_trailer_plate_ids(self, tree):
        plate_ids = []
        trailer_plates = tree.findall('.//cac:TransportHandlingUnit/cac:TransportEquipment', namespaces=UBL_NAMESPACES)
        existing_plates = dict(self.env['l10n_tr_edi.vehicle.plate']._read_group(
            [('plate_number_type', '=', 'trailer')], ['name'], ['id:min'],
        ))

        for plate in trailer_plates:
            if not (plate_name := self._l10n_tr_edi_get_tag_text('./cbc:ID', plate)):
                continue
            if plate_name in existing_plates:
                plate_ids.append(existing_plates[plate_name])
            else:
                trailer_plate = self.env['l10n_tr_edi.vehicle.plate'].create({
                    'name': plate_name,
                    'plate_number_type': 'trailer',
                })
                plate_ids.append(trailer_plate.id)
        return plate_ids

    def _l10n_tr_edi_import_drivers(self, tree):
        ResPartner = self.env['res.partner']
        # TODO Change domain if is_company is stored
        existing_partners = dict(ResPartner.with_context(active_test=False)._read_group(
            [('country_id.code', '=', 'TR'), ('has_vat', '=', True)], ['name'], ['id:min'],
        ))
        country_id = self.env.ref('base.tr', raise_if_not_found=False)
        driver_ids = []
        partners_to_create = []
        for driver in tree.findall('.//cac:DriverPerson', namespaces=UBL_NAMESPACES):
            name = f"{self._l10n_tr_edi_get_tag_text('./cbc:FirstName', driver)} {self._l10n_tr_edi_get_tag_text('./cbc:FamilyName', driver)}"
            if name in existing_partners:
                driver_ids.append(existing_partners[name])
            else:
                partners_to_create.append({
                    'name': name,
                    'vat': self._l10n_tr_edi_get_tag_text('./cbc:NationalityID', driver),
                    'country_id': country_id.id
                })
        if partners_to_create:
            partner_id = ResPartner.with_context(no_vat_validation=True).create(partners_to_create)
            driver_ids += partner_id.ids
        return driver_ids

    def _l10n_tr_edi_import_matbudan_data(self, tree):
        additional_doc_infos = tree.findall('.//cac:AdditionalDocumentReference', namespaces=UBL_NAMESPACES)
        for doc in additional_doc_infos:
            if self._l10n_tr_edi_get_tag_text('./cbc:DocumentType', doc) == 'MATBU':
                return {
                    'l10n_tr_edi_delivery_date': self._l10n_tr_edi_get_tag_text('./cbc:IssueDate', doc),
                    'l10n_tr_edi_delivery_printed_number': self._l10n_tr_edi_get_tag_text('./cbc:ID', doc)
                }

    def _l10n_tr_edi_import_partners(self, tree):
        xpath_to_field = {
            './/cac:DespatchSupplierParty/cac:Party': 'partner_id',
            './/cac:CarrierParty': 'l10n_tr_edi_carrier_id',
            './/cac:BuyerCustomerParty/cac:Party': 'l10n_tr_edi_buyer_id',
            './/cac:SellerSupplierParty/cac:Party': 'l10n_tr_edi_seller_supplier_id',
            './/cac:OriginatorCustomerParty/cac:Party': 'l10n_tr_edi_buyer_originator_id',
        }

        partner_data = [
            (xpath, self._l10n_tr_edi_get_partner_vals_from_xml(tree, xpath))
            for xpath in xpath_to_field
        ]
        partner_data = {xpath: vals for xpath, vals in partner_data if vals}

        existing_partners = self.env['res.partner'].with_context(active_test=False).search_read(
            ['|', ('vat', 'in', [vals.get('vat') for vals in partner_data.values() if vals.get('vat')]),
             ('name', 'in', [vals.get('name') for vals in partner_data.values() if vals.get('name')])],
            ['id', 'vat', 'name'],
        )
        existing_dict = {partner['vat'] or partner['name']: partner['id'] for partner in existing_partners}

        partners_vals = {}
        for xpath, vals in partner_data.items():
            key = vals.get('vat') or vals.get('name')
            partners_vals[xpath_to_field[xpath]] = existing_dict.get(key) or self._l10n_tr_edi_create_partner_from_xml(vals)

        return partners_vals

    def _l10n_tr_edi_import_edispatch_fields(self, tree):
        vals = {
            'l10n_tr_vehicle_plate': self._l10n_tr_edi_import_vehicle_plate(tree),
            'l10n_tr_edi_trailer_plate_ids': self._l10n_tr_edi_import_trailer_plate_ids(tree),
            'l10n_tr_edi_driver_ids': self._l10n_tr_edi_import_drivers(tree),
            'l10n_tr_edi_delivery_notes': self._l10n_tr_edi_get_tag_text('./cbc:Note', tree),
            'l10n_tr_edi_dispatch_type': self._l10n_tr_edi_get_tag_text('./cbc:DespatchAdviceTypeCode', tree),
        }

        if vals['l10n_tr_edi_dispatch_type'] == 'MATBUDAN' and (matbu_info := self._l10n_tr_edi_import_matbudan_data(tree)):
            vals.update(matbu_info)
        return vals

    def _l10n_tr_edi_import_receipt_line_commands(self, tree):
        data = self._l10n_tr_edi_import_receipt_lines(tree)
        existing_moves = {move.product_id.id: move.id for move in self.move_ids}
        move_commands = []
        for value in data:
            product_id = value['product_id']
            if product_id in existing_moves:
                move_commands.append(Command.update(existing_moves[product_id], {'product_uom_qty': value['product_uom_qty']}))
            else:
                move_commands.append(Command.create(value))
        return move_commands

    def action_l10n_tr_edi_update_data_from_xml(self):
        for picking in self:
            if not (attachment := picking.l10n_tr_edi_edispatch_xml_id):
                continue
            file_data = next(iter(self.env['account.move']._to_files_data(attachment)), None)
            if file_data is None:
                continue
            picking._l10n_tr_edi_update_data_from_xml(file_data)

    def _l10n_tr_edi_update_data_from_xml(self, file_data):
        tree = file_data['xml_tree']
        # Dispatch Scheduled Date & Time
        scheduled_datetime = self._l10n_tr_edi_get_tag_text('./cbc:IssueDate', tree) + " " + self._l10n_tr_edi_get_tag_text('./cbc:IssueTime', tree)

        vals_to_update = {
            'scheduled_date': scheduled_datetime,
            'l10n_tr_edi_uuid': self._l10n_tr_edi_get_tag_text('./cbc:UUID', tree),
            'origin': self.origin or self._l10n_tr_edi_get_tag_text('./cbc:ID', tree),  # sequence of the e-Receipt obtained from XML.
            'move_ids': self._l10n_tr_edi_import_receipt_line_commands(tree),
        }

        # Import Partners (Supplier, Carrier, Buyer, Seller, Originator)
        vals_to_update.update(self._l10n_tr_edi_import_partners(tree))

        # Import e-Dispatch Fields
        vals_to_update.update(self._l10n_tr_edi_import_edispatch_fields(tree))

        self.write(vals_to_update)
        if self.picking_type_code == 'incoming' and (provider := self._l10n_tr_edi_get_provider()):
            if twin := self.env['l10n_tr_edi.document'].search([
                ('company_id', '=', self.company_id.id),
                ('document_type', '=', 'edispatch'),
                ('uuid', '=', self.l10n_tr_edi_uuid),
                ('picking_id', '!=', self.id),
            ], limit=1):
                if self.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type == 'edispatch'):
                    # This transfer has its own e-Dispatch already: it cannot take another one's.
                    raise UserError(self.env._(
                        "This e-Dispatch is already on %(receipt)s.", receipt=twin.picking_id.display_name,
                    ))
                self.message_post(body=self.env._(
                    "This e-Dispatch was already imported on %(receipt)s: its e-Document stays there.",
                    receipt=twin.picking_id.display_name,
                ))
            # A received e-Dispatch was accepted by the GİB; the provider holds its documents.
            self._l10n_tr_edi_set_document_state('accepted', provider, name=self._l10n_tr_edi_get_tag_text('./cbc:ID', tree))
        self.message_post(body=_("Record updated from e-Receipt successfully."), attachment_ids=[file_data['attachment'].id])

    def _l10n_tr_create_receipts_from_attachment(self, attachments):
        files_with_errors = []
        picking_ids = self.env['stock.picking']
        warehouse = self.env.user._get_default_warehouse_id()
        attachments_data = self.env['account.move']._to_files_data(attachments)
        for attachment in attachments_data:
            # If any error occurs in parsing the XML, the 'xml_tree' key will be None.
            if attachment['xml_tree'] is None:
                files_with_errors.append(attachment['name'])
                continue
            picking = self.create({
                'picking_type_id': warehouse.in_type_id.id,
                'location_dest_id': warehouse.lot_stock_id.id,
            })
            picking._l10n_tr_edi_update_data_from_xml(attachment)
            picking_ids |= picking
        return picking_ids, files_with_errors

    def l10n_tr_import_ereceipts(self, attachment_ids):
        result = {}

        attachments_to_process = self.env['ir.attachment'].browse(attachment_ids)
        picking_ids, files_with_errors = self._l10n_tr_create_receipts_from_attachment(attachments_to_process)
        if picking_ids:
            action_vals = {
                'type': 'ir.actions.act_window',
                'name': _("Imported E-Receipts"),
                'res_model': 'stock.picking',
                'domain': [('id', 'in', picking_ids.ids)],
            }
            if len(picking_ids) == 1:
                action_vals.update({
                    'views': [[False, "form"]],
                    'view_mode': 'form',
                    'res_id': picking_ids[0].id,
                })
            else:
                action_vals.update({
                    'views': [[False, "list"], [False, "form"]],
                    'view_mode': 'list, form',
                })
            result['action'] = action_vals
        if files_with_errors:
            result['skipped_xmls'] = files_with_errors
        return result

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_l10n_tr_edi_fetch_received_dispatches(self):
        self._l10n_tr_edi_fetch_dispatches()

    def _cron_l10n_tr_edi_fetch_purchase_response_status(self, batch_size=100):
        domain = Domain.OR(self._l10n_tr_edi_get_response_status_domains('incoming'))
        self.search(domain, limit=batch_size)._l10n_tr_edi_fetch_response_status(from_cron=True)

    def _cron_l10n_tr_edi_fetch_sale_response_status(self, batch_size=100):
        domain = Domain.OR(self._l10n_tr_edi_get_response_status_domains('outgoing'))
        self.search(domain, limit=batch_size)._l10n_tr_edi_fetch_response_status(from_cron=True)
