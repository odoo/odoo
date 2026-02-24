import uuid

from markupsafe import Markup
from io import BytesIO
from lxml import etree

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node
from odoo.tools.xml_utils import find_xml_value

from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_tr_nilvera_uuid = fields.Char(
        string="Nilvera Document UUID",
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
    )
    l10n_tr_nilvera_dispatch_type = fields.Selection(
        string="Dispatch Type",
        help="Used to populate the type of dispatch.",
        selection=[
            ('SEVK', "Online"),
            ('MATBUDAN', "Pre-printed"),
        ],
        default='SEVK',
        tracking=True,
        copy=False,
    )
    l10n_tr_nilvera_carrier_id = fields.Many2one(
        string="Carrier (TR)",
        help="Used when the dispatch is made through a third-party carrier company. Populating this makes the Vehicle Plate and Drivers optional.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_nilvera_buyer_id = fields.Many2one(
        string="Buyer",
        help="Used for the original party who purchases the good when the Delivery Address is for another recipient",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_nilvera_seller_supplier_id = fields.Many2one(
        string="Seller Supplier",
        help="Used for the information of the supplier of the goods in the delivery note.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_nilvera_buyer_originator_id = fields.Many2one(
        string="Buyer Originator",
        help="Used for the original initiator of the goods acquisition and requesting process.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_nilvera_delivery_printed_number = fields.Char(string="Printed Delivery Note Number", copy=False)
    l10n_tr_nilvera_delivery_date = fields.Date(string="Printed Delivery Note Date", copy=False)
    l10n_tr_vehicle_plate = fields.Many2one(
        string="Vehicle Plate",
        help="Used to input the plate number of the truck.",
        comodel_name='l10n_tr.nilvera.trailer.plate',
        domain="[('plate_number_type', '=', 'vehicle')]",
        copy=False,
    )
    l10n_tr_nilvera_trailer_plate_ids = fields.Many2many(
        string="Trailer Plates",
        help="Used to input the plate numbers of the trailers attached to the truck.",
        comodel_name='l10n_tr.nilvera.trailer.plate',
        domain="[('plate_number_type', '=', 'trailer')]",
        relation='l10n_tr_nilvera_delivery_vehicle_rel',
        copy=False,
    )
    l10n_tr_nilvera_driver_ids = fields.Many2many(
        string="Drivers",
        help="Used for the individuals driving the truck.",
        comodel_name='res.partner',
        copy=False,
    )
    l10n_tr_nilvera_delivery_notes = fields.Char(string="Delivery Notes", copy=False)
    l10n_tr_nilvera_send_status = fields.Selection(
        string="Nilvera Status",
        selection=[
            ('error', "Error"),
            ('not_sent', "Not sent"),
            ('sent', "Sent and waiting response"),
            ('succeed', "Successful"),
            ('waiting', "Waiting"),
            ('unknown', "Unknown"),
        ],
        copy=False,
        readonly=True,
        default='not_sent',
    )
    l10n_tr_nilvera_edispatch_warnings = fields.Json(compute='_compute_edispatch_warnings')
    l10n_tr_nilvera_edispatch_xml_file = fields.Binary(
        string="Nilvera E-Despatch XML File",
        copy=False,
        attachment=True,
    )
    l10n_tr_nilvera_edispatch_xml_id = fields.Many2one(
        "ir.attachment",
        string="Nilvera E-Despatch XML",
        compute='_compute_l10n_tr_nilvera_edispatch_xml_id',
    )

    @api.depends('l10n_tr_nilvera_edispatch_xml_file')
    def _compute_l10n_tr_nilvera_edispatch_xml_id(self):
        """
        Helper to retreive Attachment from Binary fields
        This is needed because fields.Many2one('ir.attachment') makes all
        attachments available to the user.
        """
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('res_field', '=', 'l10n_tr_nilvera_edispatch_xml_file')
        ])
        picking_vals = {att.res_id: att for att in attachments}
        for picking in self:
            picking.l10n_tr_nilvera_edispatch_xml_id = picking_vals.get(picking._origin.id, False)

    @api.depends(
        'l10n_tr_nilvera_carrier_id', 'l10n_tr_nilvera_buyer_id', 'l10n_tr_nilvera_seller_supplier_id',
        'l10n_tr_nilvera_buyer_originator_id', 'l10n_tr_nilvera_delivery_printed_number',
        'l10n_tr_nilvera_delivery_date', 'l10n_tr_vehicle_plate', 'l10n_tr_nilvera_trailer_plate_ids',
        'l10n_tr_nilvera_driver_ids', 'partner_id',
    )
    def _compute_edispatch_warnings(self):
        for picking in self:
            if (
                picking.country_code == "TR"
                and picking.picking_type_code == "outgoing"
                and picking.state in {"assigned", "done"}
            ):
                picking.l10n_tr_nilvera_edispatch_warnings = picking._l10n_tr_validate_edispatch_fields()
            else:
                picking.l10n_tr_nilvera_edispatch_warnings = False

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if picking.country_code != 'TR' or picking.picking_type_code != 'outgoing' or picking.state != 'done':
                continue
            else:
                picking.message_post(
                    body=_("e-Dispatch will not be generated as the Delivery Address is not set.")
                )
        return res

    def _l10n_tr_validate_edispatch_on_done(self):
        partners = (
            self.partner_id
            | self.l10n_tr_nilvera_buyer_id
            | self.l10n_tr_nilvera_seller_supplier_id
            | self.l10n_tr_nilvera_buyer_originator_id
        )
        partners_requiring_tax_office = (
            self.company_id.partner_id
            | self.partner_id.commercial_partner_id
            | self.l10n_tr_nilvera_carrier_id
        ).filtered(lambda p: p.l10n_tr_nilvera_customer_status == 'einvoice')

        error_messages = (
            partners._l10n_tr_nilvera_validate_partner_details() |
            partners_requiring_tax_office._l10n_tr_nilvera_validate_partner_details(tax_office_required=True)
        )

        if self.l10n_tr_nilvera_dispatch_type == 'MATBUDAN':
            if not self.l10n_tr_nilvera_delivery_date:
                error_messages['invalid_matbudan_date'] = {
                    'message': _("Printed Delivery Note Date is required."),
                    'level': 'danger',
                }
            if (
                not self.l10n_tr_nilvera_delivery_printed_number
                or len(self.l10n_tr_nilvera_delivery_printed_number) != 16
            ):
                error_messages['invalid_matbudan_number'] = {
                    'message': _("Printed Delivery Note Number of 16 characters is required."),
                    'level': 'danger',
                }

        invalid_country_drivers = self.l10n_tr_nilvera_driver_ids.filtered(
            lambda driver: not driver.country_id or driver.country_id.code != 'TR'
        )
        invalid_tckn_drivers = (self.l10n_tr_nilvera_driver_ids - invalid_country_drivers).filtered(
            lambda driver: not driver.vat or (driver.vat and len(driver.vat) != 11)
        )

        if drivers := len(invalid_country_drivers):
            error_messages['invalid_driver_country'] = {
                'message': _(
                    "Only Drivers from Türkiye are valid. Please update the Country and enter a valid TCKN in the Tax ID."
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

        if (
            not self.l10n_tr_nilvera_carrier_id
            and not self.l10n_tr_nilvera_driver_ids
            and not self.l10n_tr_vehicle_plate
        ):
            error_messages['required_carrier_details'] = {
                'message': _("Carrier is required (optional when both the Driver and Vehicle Plate are filled)."),
                'level': 'danger',
            }

        elif not self.l10n_tr_nilvera_carrier_id and not self.l10n_tr_nilvera_driver_ids:
            error_messages['required_driver_details'] = {
                'message': _("At least one Driver is required."),
                'level': 'danger',
            }

        elif not self.l10n_tr_nilvera_carrier_id and not self.l10n_tr_vehicle_plate:
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

    def _l10n_tr_generate_edispatch_xml(self):
        drivers = []
        for driver in self.l10n_tr_nilvera_driver_ids:
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
            'uuid': self.l10n_tr_nilvera_uuid,
            'id': self._get_nilvera_document_serial_number(),
            'picking': self,
            'current_company': self.env.company.partner_id,
            'issue_date': scheduled_date_local.date().strftime('%Y-%m-%d'),
            'issue_time': scheduled_date_local.time().strftime('%H:%M:%S'),
            'actual_date': date_done_local.strftime('%Y-%m-%d'),
            'actual_time': date_done_local.strftime('%H:%M:%S'),
            'line_count': len(self.move_ids),
            'printed_date': self.l10n_tr_nilvera_delivery_date and self.l10n_tr_nilvera_delivery_date.strftime('%Y-%m-%d'),
            'drivers': drivers,
            'default_tckn': '22222222222',
            'dispatch_scenario': 'TEMELIRSALIYE',
            'copy_indicator': 'false',
        }
        xml_content = self.env['ir.qweb']._render(
            'l10n_tr_nilvera_edispatch.l10n_tr_edispatch_format',
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
            'res_field': 'l10n_tr_nilvera_edispatch_xml_file',
            'mimetype': 'application/xml',
        })
        self.invalidate_recordset(fnames=['l10n_tr_nilvera_edispatch_xml_id', 'l10n_tr_nilvera_edispatch_xml_file'])
        self.message_post(
            body=_("e-Dispatch XML file generated successfully."),
            attachment_ids=[attachment.id],
            subtype_xmlid='mail.mt_note',
        )

    def _l10n_tr_nilvera_submit_document(self, xml_file, post_series=True):
        """
        Submits an e-despatch document to Nilvera for processing.

        :param xml_file: The XML file to be submitted.
        :type xml_file: file-like object
        :param post_series: Whether to attempt posting the series/sequence to Nilvera if it is missing.
                            Defaults to True. Useful for avoiding an infinite loop.
        :type post_series: bool
        :raises UserError: If the API key lacks necessary rights (401 or 403 responses), if the response
                            indicates a client error (4xx), or if a server error occurs (500).
        :return: None
        """
        with _get_nilvera_client(self.env._, self.env.company) as client:
            response = client.request(
                "POST",
                endpoint='/edespatch/Send/Xml',
                params={'Alias': self.partner_id.l10n_tr_nilvera_edispatch_alias_id.name or 'urn:mail:irsaliyepk@gib.gov.tr'},
                files={'file': (xml_file.name, xml_file, 'application/xml')},
                handle_response=False,
            )

        if response.status_code == 200:
            self.l10n_tr_nilvera_send_status = 'sent'
        elif response.status_code in {401, 403}:
            raise UserError(_("Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."))
        elif 400 <= response.status_code < 500:
            error_message, error_codes = client._get_error_message_with_codes_from_response(response)

            # If the sequence/series is not found on Nilvera, add it then retry.
            if 3009 in error_codes and post_series:
                self._l10n_tr_nilvera_post_series(client)
                xml_file.seek(0)  # reset stream before retry, as previous POST moved the buffer to the EOF
                return self._l10n_tr_nilvera_submit_document(xml_file, post_series=False)
            raise UserError(error_message)
        elif response.status_code == 500:
            raise UserError(_("Server error from Nilvera, please try again later."))

        self.message_post(body=_("The dispatch has been successfully sent to Nilvera."))

    def _l10n_tr_nilvera_post_series(self, client):
        if not self.picking_type_id.sequence_code:
            return

        client.request(
            "POST",
            endpoint="/edespatch/Series",
            json={
                'Name': self.picking_type_id.sequence_code.upper(),
                'IsActive': True,
                'IsDefault': False,
            },
        )

    def _l10n_tr_nilvera_get_submitted_document_status(self):
        for company, stock_pickings in self.grouped("company_id").items():
            with _get_nilvera_client(self.env._, company) as client:
                for stock_picking in stock_pickings:
                    response = client.request(
                        "GET",
                        endpoint=f"/edespatch/Sale/{stock_picking.l10n_tr_nilvera_uuid}/Status",
                    )

                    nilvera_status = response.get('DespatchStatus', {}).get('Code')
                    if nilvera_status in dict(stock_pickings._fields['l10n_tr_nilvera_send_status'].selection):
                        stock_pickings.l10n_tr_nilvera_send_status = nilvera_status
                        if nilvera_status == 'error':
                            stock_pickings.message_post(
                                body=Markup(
                                    "%s<br/>%s - %s<br/>"
                                ) % (
                                    _("The dispatch couldn't be sent to the recipient."),
                                    response.get('DespatchStatus', {}).get('Description'),
                                    response.get('DespatchStatus', {}).get('DetailDescription'),
                                )
                            )
                    else:
                        stock_pickings.message_post(body=_("The dispatch status couldn't be retrieved from Nilvera."))

    def l10n_tr_nilvera_get_dispatch_status(self):
        self._l10n_tr_nilvera_get_submitted_document_status()

    def action_send_edispatch_xml(self):
        if self.l10n_tr_nilvera_edispatch_warnings:
            raise UserError(_("Cannot send the XML when there are warnings."))
        self._l10n_tr_generate_edispatch_xml()
        xml_file = BytesIO(self.l10n_tr_nilvera_edispatch_xml_id.raw or b'')
        xml_file.name = self.l10n_tr_nilvera_edispatch_xml_id.name or ''
        self._l10n_tr_nilvera_submit_document(xml_file)

    def action_generate_l10n_tr_edispatch_xml(self, is_list=False):
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
        return super()._get_mail_thread_data_attachments() + self.l10n_tr_nilvera_edispatch_xml_id

    def _get_tag_text(self, xpath, tree, default=''):
        return find_xml_value(xpath, tree, UBL_NAMESPACES) or default

    def _get_partner_vals_from_xml(self, tree, xpath):
        party = tree.find(xpath, namespaces=UBL_NAMESPACES)
        if party is None:
            return
        return {
            'name': self._get_tag_text('./cac:PartyName/cbc:Name', party) or
                    f"{self._get_tag_text('./cac:Person/cbc:FirstName', party)} {self._get_tag_text('./cac:Person/cbc:FamilyName', party)}",
            'vat': self._get_tag_text('./cac:PartyIdentification/cbc:ID[@schemeID="VKN" or @schemeID="TCKN"]', party),
            'street': self._get_tag_text('./cac:PostalAddress/cbc:StreetName', party),
            'city': self._get_tag_text('./cac:PostalAddress/cbc:CitySubdivisionName', party),
            'zip': self._get_tag_text('./cac:PostalAddress/cbc:PostalZone', party),
            'state': self._get_tag_text('./cac:PostalAddress/cbc:CityName', party),
            'country': self._get_tag_text('./cac:PostalAddress/cac:Country/cbc:Name', party),
            'phone': self._get_tag_text('./cac:Contact/cbc:Telephone', party),
            'email': self._get_tag_text('./cac:Contact/cbc:ElectronicMail', party),
        }

    def _create_partner_from_xml(self, partner_vals):
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
            partner_vals['l10n_tr_nilvera_edispatch_customs_zip'] = partner_vals.pop('zip', '')

        partner = self.env['res.partner'].with_context(no_vat_validation=True).create(partner_vals)
        return partner.id

    def _find_or_create_products_from_xml(self, receipt_lines):
        product_names = [
            self._get_tag_text('./cac:Item/cbc:Name', receipt) for receipt in receipt_lines
        ]
        existing_products = dict(self.env['product.product']._read_group(
            [('name', 'in', product_names)], ['name'], ['id:min'],
        ))

        products_to_create = []
        for receipt in receipt_lines:
            name = self._get_tag_text('./cac:Item/cbc:Name', receipt)
            if name not in existing_products:
                unece_code = receipt.find('./cbc:DeliveredQuantity', namespaces=UBL_NAMESPACES).get('unitCode', '')
                products_to_create.append({
                    'name': name,
                    'default_code': self._get_tag_text('./cac:Item/cac:SellersItemIdentification/cbc:ID', receipt),
                    'uom_id': self.env['uom.uom']._get_uom_from_unece_code(unece_code).id,
                })

        if products_to_create:
            created_products = self.env['product.product'].create(products_to_create)
            existing_products.update({product.name: product.id for product in created_products})

        return existing_products

    def _import_receipt_lines(self, tree):
        receipt_lines = tree.findall('./cac:DespatchLine', namespaces=UBL_NAMESPACES)
        if not receipt_lines:
            return []

        products_dict = self._find_or_create_products_from_xml(receipt_lines)
        source_location = self.picking_type_id.default_location_src_id

        values = []
        for receipt in receipt_lines:
            name = self._get_tag_text('./cac:Item/cbc:Name', receipt)
            values.append({
                'description_picking': name,
                'product_id': products_dict[name],
                'product_uom_qty': self._get_tag_text('./cbc:DeliveredQuantity', receipt),
                'picking_id': self.id,
                'location_dest_id': self.location_dest_id.id,
                'location_id': source_location.id,
            })
        return values

    def _import_vehicle_plate(self, tree):
        vehicle_plate = self._get_tag_text('.//cac:RoadTransport/cbc:LicensePlateID', tree)
        if not vehicle_plate:
            return
        vehicle_plate_id = self.env['l10n_tr.nilvera.trailer.plate'].search_fetch(
            [('name', '=', vehicle_plate), ('plate_number_type', '=', 'vehicle')], ['id'], limit=1,
        )
        if not vehicle_plate_id:
            vehicle_plate_id = self.env['l10n_tr.nilvera.trailer.plate'].create({
                'name': vehicle_plate,
                'plate_number_type': 'vehicle',
            })
        return vehicle_plate_id.id

    def _import_trailer_plate_ids(self, tree):
        plate_ids = []
        trailer_plates = tree.findall('.//cac:TransportHandlingUnit/cac:TransportEquipment', namespaces=UBL_NAMESPACES)
        existing_plates = dict(self.env['l10n_tr.nilvera.trailer.plate']._read_group(
            [('plate_number_type', '=', 'trailer')], ['name'], ['id:min'],
        ))

        for plate in trailer_plates:
            if not (plate_name := self._get_tag_text('./cbc:ID', plate)):
                continue
            if plate_name in existing_plates:
                plate_ids.append(existing_plates[plate_name])
            else:
                trailer_plate = self.env['l10n_tr.nilvera.trailer.plate'].create({
                    'name': plate_name,
                    'plate_number_type': 'trailer',
                })
                plate_ids.append(trailer_plate.id)
        return plate_ids

    def _import_drivers(self, tree):
        ResPartner = self.env['res.partner']
        # TODO Change domain if is_company is stored
        existing_partners = dict(ResPartner.with_context(active_test=False)._read_group(
            [('country_id.code', '=', 'TR'), ('vat', 'not in', [False, 'na', 'NA', '/'])], ['name'], ['id:min'],
        ))
        country_id = self.env.ref('base.tr', raise_if_not_found=False)
        driver_ids = []
        partners_to_create = []
        for driver in tree.findall('.//cac:DriverPerson', namespaces=UBL_NAMESPACES):
            name = f"{self._get_tag_text('./cbc:FirstName', driver)} {self._get_tag_text('./cbc:FamilyName', driver)}"
            if name in existing_partners:
                driver_ids.append(existing_partners[name])
            else:
                partners_to_create.append({
                    'name': name,
                    'vat': self._get_tag_text('./cbc:NationalityID', driver),
                    'country_id': country_id.id
                })
        if partners_to_create:
            partner_id = ResPartner.with_context(no_vat_validation=True).create(partners_to_create)
            driver_ids += partner_id.ids
        return driver_ids

    def _import_matbudan_data(self, tree):
        additional_doc_infos = tree.findall('.//cac:AdditionalDocumentReference', namespaces=UBL_NAMESPACES)
        for doc in additional_doc_infos:
            if self._get_tag_text('./cbc:DocumentType', doc) == 'MATBU':
                return {
                    'l10n_tr_nilvera_delivery_date': self._get_tag_text('./cbc:IssueDate', doc),
                    'l10n_tr_nilvera_delivery_printed_number': self._get_tag_text('./cbc:ID', doc)
                }

    def _import_partners(self, tree):
        xpath_to_field = {
            './/cac:DespatchSupplierParty/cac:Party': 'partner_id',
            './/cac:CarrierParty': 'l10n_tr_nilvera_carrier_id',
            './/cac:BuyerCustomerParty/cac:Party': 'l10n_tr_nilvera_buyer_id',
            './/cac:SellerSupplierParty/cac:Party': 'l10n_tr_nilvera_seller_supplier_id',
            './/cac:OriginatorCustomerParty/cac:Party': 'l10n_tr_nilvera_buyer_originator_id',
        }

        partner_data = [
            (xpath, self._get_partner_vals_from_xml(tree, xpath))
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
            partners_vals[xpath_to_field[xpath]] = existing_dict.get(key) or self._create_partner_from_xml(vals)

        return partners_vals

    def _import_edispatch_fields(self, tree):
        vals = {
            'l10n_tr_vehicle_plate': self._import_vehicle_plate(tree),
            'l10n_tr_nilvera_trailer_plate_ids': self._import_trailer_plate_ids(tree),
            'l10n_tr_nilvera_driver_ids': self._import_drivers(tree),
            'l10n_tr_nilvera_delivery_notes': self._get_tag_text('./cbc:Note', tree),
            'l10n_tr_nilvera_dispatch_type': self._get_tag_text('./cbc:DespatchAdviceTypeCode', tree),
        }

        if vals['l10n_tr_nilvera_dispatch_type'] == 'MATBUDAN' and (matbu_info := self._import_matbudan_data(tree)):
            vals.update(matbu_info)
        return vals

    def _update_data_from_xml(self, file_data):
        tree = file_data['xml_tree']
        # Dispatch Scheduled Date & Time
        scheduled_datetime = self._get_tag_text('./cbc:IssueDate', tree) + " " + self._get_tag_text('./cbc:IssueTime', tree)

        vals_to_update = {
            'scheduled_date': scheduled_datetime,
            'origin': self._get_tag_text('./cbc:ID', tree),  # sequence of the e-Receipt obtained from XML.
            'move_ids': [Command.create(value) for value in self._import_receipt_lines(tree)],
        }

        # Import Partners (Supplier, Carrier, Buyer, Seller, Originator)
        vals_to_update.update(self._import_partners(tree))

        # Import e-Dispatch Fields
        vals_to_update.update(self._import_edispatch_fields(tree))

        self.write(vals_to_update)
        self.message_post(body=_("e-Receipt uploaded successfully."), attachment_ids=[file_data['attachment'].id])

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
            picking._update_data_from_xml(attachment)
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

    def _get_nilvera_document_serial_number(self):
        """
        Returns the serial number for the e-Dispatch document in a format accepted by Nilvera.
        The format is: '[Picking Type Code][Year (YYYY)][Sequence Number of 9 digits padded with 0]'
        Example: 'OUT2025123456789'
        """
        sequence_number = self.name.removeprefix(self.picking_type_id.sequence_id.prefix or '').removesuffix(self.picking_type_id.sequence_id.suffix or '')
        return f"{self.picking_type_id.sequence_code.upper()}{self.scheduled_date.year}{sequence_number.zfill(9)}"
