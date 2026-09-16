import base64

import markupsafe

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from odoo.addons.l10n_ro_edi_stock.models.etransport_api import ETransportAPI
from odoo.addons.l10n_ro_edi_stock.models.mixin_stock_consignment import (
    STATE_CODES,
    _eu_country_vat,
)

_debug = DebugLog(__name__)


class Picking(models.Model):
    _inherit = "stock.picking"

    # Document fields
    l10n_ro_edi_stock_document_ids = fields.One2many(
        comodel_name="l10n_ro_edi.document",
        inverse_name="picking_id",
    )

    ################################################################################
    # Compute Methods
    ################################################################################

    @api.depends("picking_type_code")
    def _compute_l10n_ro_edi_stock_enable(self):
        super()._compute_l10n_ro_edi_stock_enable()
        for picking in self:
            picking.l10n_ro_edi_stock_enable = (
                picking.l10n_ro_edi_stock_enable
                and picking.picking_type_code != "internal"
            )

    def _l10n_ro_edi_stock_is_shipped(self) -> bool:
        _debug.logic("etransport_is_shipped", pickings=self)
        return self.state == "done"

    ################################################################################
    # Validation methods
    ################################################################################

    def button_validate(self):
        # EXTENDS 'stock'

        # Validate the carrier first because it cannot be changed after the super call
        _debug.pipeline("etransport_picking_validate", pickings=self)
        self._l10n_ro_edi_stock_check_carrier()

        return super().button_validate()

    def _l10n_ro_edi_stock_check_carrier(self):
        _debug.logic("etransport_validate_carrier", pickings=self)
        for picking in self.filtered(self._l10n_ro_edi_stock_is_carrier_check_required):
            # validate carrier
            if not picking.carrier_id:
                raise UserError(
                    _(
                        "The picking %(picking_name)s is missing a delivery carrier.",
                        picking_name=picking.name,
                    )
                )

            # validate carrier partner
            if not picking.carrier_id.l10n_ro_edi_stock_partner_id:
                raise UserError(
                    _(
                        "The delivery carrier of %(picking_name)s is missing the partner field value.",
                        picking_name=picking.name,
                    )
                )

    @api.model
    def _l10n_ro_edi_stock_is_carrier_check_required(self, picking):
        # To be overridden by stock.picking.batch
        return picking.l10n_ro_edi_stock_enable

    @api.model
    def _l10n_ro_edi_stock_get_data_errors(self, data: dict):
        _debug.logic("edi_delivery_validate", regime="ro", pickings=self)
        errors = []

        # API access token
        if not data["company_id"].l10n_ro_edi_access_token:
            errors.append(
                _(
                    "Romanian access token not found. Please generate or fill it in the settings."
                )
            )

        # carrier partner fields
        partner = data["transport_partner_id"]
        missing_carrier_partner_fields = []

        if not partner.vat:
            missing_carrier_partner_fields.append(_("VAT"))

        if not partner.city:
            missing_carrier_partner_fields.append(_("City"))

        if not partner.street:
            missing_carrier_partner_fields.append(_("Street"))

        if len(missing_carrier_partner_fields) == 1:
            errors.append(
                _(
                    "The delivery carrier partner is missing the %(field_name)s field.",
                    field_name=missing_carrier_partner_fields[0],
                )
            )
        elif len(missing_carrier_partner_fields) > 1:
            errors.append(
                _(
                    "The delivery carrier partner is missing following fields: %(field_names)s",
                    field_names=", ".join(missing_carrier_partner_fields),
                )
            )

        # operation type
        if not data["l10n_ro_edi_stock_operation_type"]:
            errors.append(_("Operation type is missing."))
            return errors  # return prematurely because a lot of fields depend on the operation type

        # operation scope
        if not data["l10n_ro_edi_stock_operation_scope"]:
            errors.append(_("Operation scope is missing."))

        # vehicle & trailer numbers
        if not data["l10n_ro_edi_stock_vehicle_number"]:
            errors.append(_("Vehicle number is missing."))

        # All filled-in vehicle and trailer numbers must be unique
        license_plates = [
            num
            for num in (
                data["l10n_ro_edi_stock_vehicle_number"],
                data["l10n_ro_edi_stock_trailer_1_number"],
                data["l10n_ro_edi_stock_trailer_2_number"],
            )
            if num
        ]
        if len(license_plates) != len(set(license_plates)):
            errors.append(_("Vehicle number and trailer number fields must be unique."))

        # rate codes
        if "intrastat_code_id" in self.env["product.product"]._fields and data[
            "l10n_ro_edi_stock_operation_type"
        ] not in ("60", "70"):
            product_without_code_names = {
                move_line.product_id.name
                for move in data["stock_move_ids"]
                for move_line in move.move_line_ids
                if not move_line.product_id.intrastat_code_id.code
            }

            if product_without_code_names:
                if len(product_without_code_names) == 1:
                    (product_name,) = product_without_code_names
                    errors.append(
                        _(
                            "Product %(name)s is missing the intrastat code value.",
                            name=product_name,
                        )
                    )
                else:
                    errors.append(
                        _(
                            "Products %(names)s are missing the intrastat code value.",
                            names=", ".join(product_without_code_names),
                        )
                    )

        # Location types
        if not data["l10n_ro_edi_stock_start_loc_type"]:
            if not data["l10n_ro_edi_stock_end_loc_type"]:
                errors.append(_("Both 'End' and 'Start Location Type' are missing"))
            else:
                errors.append(_("'Start Location Type' is missing"))

            return errors  # return prematurely because all the start location fields depend on this field

        if not data["l10n_ro_edi_stock_end_loc_type"]:
            errors.append(_("'End Location Type' is missing"))
            return errors  # return prematurely because all the end location fields depend on this field

        # Location fields
        for location in ("start", "end"):
            loc_value = data[f"l10n_ro_edi_stock_{location}_loc_type"]
            loc_group = (
                _("'Start Location'") if location == "start" else _("'End Location'")
            )

            if loc_value == "bcp" and not data[f"l10n_ro_edi_stock_{location}_bcp"]:
                errors.append(
                    _(
                        "The border crossing point is missing under %(location_group)s",
                        location_group=loc_group,
                    )
                )
            elif (
                loc_value == "customs"
                and not data[f"l10n_ro_edi_stock_{location}_customs_office"]
            ):
                errors.append(
                    _(
                        "The customs office is missing under %(location_group)s",
                        location_group=loc_group,
                    )
                )
            elif loc_value == "location":
                match data["picking_type_id"].code:
                    case "outgoing":
                        partner = (
                            data["picking_type_id"].warehouse_id.partner_id
                            if location == "start"
                            else data["partner_id"]
                        )
                    case "incoming":
                        partner = (
                            data["picking_type_id"].warehouse_id.partner_id
                            if location == "end"
                            else data["partner_id"]
                        )
                    case _other:
                        errors.append(
                            _("Invalid picking type %(type_code)s", type_code=_other)
                        )
                        continue

                missing_field_names = []
                if not partner.state_id:
                    missing_field_names.append(_("State"))
                if not partner.city:
                    missing_field_names.append(_("City"))
                if not partner.street:
                    missing_field_names.append(_("Street"))
                if not partner.zip:
                    missing_field_names.append(_("Postal Code"))

                if len(missing_field_names) == 1:
                    errors.append(
                        _(
                            "%(location_group)s is missing the %(field_name)s field.",
                            location_group=loc_group,
                            field_name=missing_field_names[0],
                        )
                    )
                elif len(missing_field_names) > 1:
                    errors.append(
                        _(
                            "%(location_group)s is missing following fields: %(field_names)s",
                            location_group=loc_group,
                            field_names=missing_field_names,
                        )
                    )

        return errors

    def _l10n_ro_edi_stock_get_fetch_data_errors(self, errors=None):
        _debug.logic("etransport_validate_fetch", pickings=self)
        if errors is None:
            errors = []
        self.check_singleton()

        if not self.company_id.l10n_ro_edi_access_token:
            errors.append(
                _(
                    "Romanian access token not found. Please generate or fill it in the settings."
                )
            )
            return errors

        match self.l10n_ro_edi_stock_state:
            case "stock_sending_failed":
                if not self._l10n_ro_edi_stock_get_last_document("stock_validated"):
                    errors.append(
                        _(
                            "This document has not been successfully sent yet because it contains errors."
                        )
                    )
                else:
                    errors.append(
                        _(
                            "This document has not been corrected yet because it contains errors."
                        )
                    )
            case "stock_validated":
                errors.append(
                    _("This document has already been successfully sent to anaf.")
                )

        return errors

    ################################################################################
    # Actions
    ################################################################################

    def action_l10n_ro_edi_stock_send_etransport(self):
        _debug.pipeline("edi_delivery_send", regime="ro", pickings=self)
        self.check_singleton()

        send_type = self.env.context.get("l10n_ro_edi_stock_send_type", "send")
        self._l10n_ro_edi_stock_send_etransport_document(send_type=send_type)

    def action_l10n_ro_edi_stock_fetch_status(self):
        _debug.pipeline("edi_delivery_status", regime="ro", pickings=self)
        self._l10n_ro_edi_stock_update_document_status()

    ################################################################################
    # Document Helpers
    ################################################################################

    def _l10n_ro_edi_stock_create_document_stock_sent(self, values: dict[str, object]):
        _debug.lifecycle("etransport_document_sent", pickings=self)
        self.check_singleton()
        return self.env["l10n_ro_edi.document"].create(
            {
                "picking_id": self.id,
                "state": "stock_sent",
                "l10n_ro_edi_stock_load_id": values["l10n_ro_edi_stock_load_id"],
                "l10n_ro_edi_stock_uit": values["l10n_ro_edi_stock_uit"],
                "attachment": base64.b64encode(values["raw_xml"].encode("utf-8")),
            }
        )

    def _l10n_ro_edi_stock_create_document_stock_sending_failed(
        self, values: dict[str, object]
    ):
        self.check_singleton()
        document = self.env["l10n_ro_edi.document"].create(
            {
                "picking_id": self.id,
                "state": "stock_sending_failed",
                "message": values["message"],
                "l10n_ro_edi_stock_load_id": values.get("l10n_ro_edi_stock_load_id"),
                "l10n_ro_edi_stock_uit": values.get("l10n_ro_edi_stock_uit"),
            }
        )

        if "raw_xml" in values:
            # when an error is thrown during data validation there will be no 'raw_xml'
            document.attachment = base64.b64encode(values["raw_xml"].encode("utf-8"))

        return document

    def _l10n_ro_edi_stock_create_document_stock_validated(
        self, values: dict[str, object]
    ):
        self.check_singleton()
        return self.env["l10n_ro_edi.document"].create(
            {
                "picking_id": self.id,
                "state": "stock_validated",
                "l10n_ro_edi_stock_load_id": values["l10n_ro_edi_stock_load_id"],
                "l10n_ro_edi_stock_uit": values["l10n_ro_edi_stock_uit"],
                "attachment": base64.b64encode(values["raw_xml"].encode("utf-8")),
            }
        )

    ################################################################################
    # Send Logic
    ################################################################################

    def _l10n_ro_edi_stock_send_etransport_document(self, send_type: str):
        """
        Send the eTransport document to anaf
        :param send_type: 'send' (initial sending of document) | 'amend' (correct the already sent document)
        """
        self.check_singleton()

        data = {
            "partner_id": self.partner_id,
            "transport_partner_id": self.carrier_id.l10n_ro_edi_stock_partner_id,
            "company_id": self.company_id,
            "scheduled_date": self.date_planned,
            "name": self.name,
            "send_type": send_type,
            "l10n_ro_edi_stock_operation_type": self.l10n_ro_edi_stock_operation_type,
            "l10n_ro_edi_stock_operation_scope": self.l10n_ro_edi_stock_operation_scope,
            "stock_move_ids": self.move_ids,
            "l10n_ro_edi_stock_vehicle_number": self.l10n_ro_edi_stock_vehicle_number,
            "l10n_ro_edi_stock_trailer_1_number": self.l10n_ro_edi_stock_trailer_1_number,
            "l10n_ro_edi_stock_trailer_2_number": self.l10n_ro_edi_stock_trailer_2_number,
            "l10n_ro_edi_stock_start_loc_type": self.l10n_ro_edi_stock_start_loc_type,
            "l10n_ro_edi_stock_end_loc_type": self.l10n_ro_edi_stock_end_loc_type,
            "l10n_ro_edi_stock_remarks": self.l10n_ro_edi_stock_remarks,
            "picking_type_id": self.picking_type_id,
            "l10n_ro_edi_stock_start_bcp": self.l10n_ro_edi_stock_start_bcp,
            "l10n_ro_edi_stock_end_bcp": self.l10n_ro_edi_stock_end_bcp,
            "l10n_ro_edi_stock_start_customs_office": self.l10n_ro_edi_stock_start_customs_office,
            "l10n_ro_edi_stock_end_customs_office": self.l10n_ro_edi_stock_end_customs_office,
            "l10n_ro_edi_stock_document_uit": self.l10n_ro_edi_stock_document_uit,
        }

        if errors := self._l10n_ro_edi_stock_get_data_errors(data=data):
            document_values = {"message": "\n".join(errors)}

            if send_type == "amend":
                last_sent_document = self._l10n_ro_edi_stock_get_last_document(
                    "stock_validated"
                )
                document_values |= {
                    "l10n_ro_edi_stock_load_id": last_sent_document.l10n_ro_edi_stock_load_id,
                    "l10n_ro_edi_stock_uit": last_sent_document.l10n_ro_edi_stock_uit,
                    "raw_xml": base64.b64decode(last_sent_document.attachment).decode(),
                }

            self._l10n_ro_edi_stock_create_document_stock_sending_failed(
                document_values
            )
            return

        raw_xml = markupsafe.Markup(
            "<?xml version='1.0' encoding='UTF-8'?>\n"
        ) + self.env["ir.qweb"]._render(
            "l10n_ro_edi_stock.l10n_ro_template_etransport",
            values=self._l10n_ro_edi_stock_get_template_data(data=data),
        )

        result = ETransportAPI().upload_data(company_id=self.company_id, data=raw_xml)

        if "error" in result:
            document_values = {"message": result["error"], "raw_xml": raw_xml}

            if send_type == "amend":
                last_sent_document = self._l10n_ro_edi_stock_get_last_document(
                    "stock_validated"
                )
                document_values |= {
                    "l10n_ro_edi_stock_load_id": last_sent_document.l10n_ro_edi_stock_load_id,
                    "l10n_ro_edi_stock_uit": last_sent_document.l10n_ro_edi_stock_uit,
                }

            self._l10n_ro_edi_stock_create_document_stock_sending_failed(
                document_values
            )
        else:
            self._l10n_ro_edi_stock_get_all_documents(
                {"stock_sending_failed", "stock_sent"}
            ).unlink()

            content = result["content"]

            if send_type == "send":
                uit = content["UIT"]
            else:
                last_validated = self._l10n_ro_edi_stock_get_last_document(
                    "stock_validated"
                )
                uit = last_validated.l10n_ro_edi_stock_uit

            self._l10n_ro_edi_stock_create_document_stock_sent(
                {
                    "l10n_ro_edi_stock_load_id": content["index_incarcare"],
                    "l10n_ro_edi_stock_uit": uit,
                    "raw_xml": raw_xml,
                }
            )

    def _l10n_ro_edi_stock_update_document_status(self):
        session = self.env["ir.egress"].session(purpose="l10n_ro_etransport")
        documents_to_delete = self.env["l10n_ro_edi.document"]
        to_fetch = self.filtered(lambda p: p.l10n_ro_edi_stock_state == "stock_sent")

        for picking in to_fetch:
            current_sending_document = picking.l10n_ro_edi_stock_document_ids.filtered(
                lambda doc: doc.state == "stock_sent"
            )[0]

            if errors := picking._l10n_ro_edi_stock_get_fetch_data_errors():
                picking._l10n_ro_edi_stock_create_document_stock_sending_failed(
                    {
                        "message": "\n".join(errors),
                        "l10n_ro_edi_stock_load_id": current_sending_document.l10n_ro_edi_stock_load_id,
                        "l10n_ro_edi_stock_uit": current_sending_document.l10n_ro_edi_stock_uit,
                        "raw_xml": base64.b64decode(
                            current_sending_document.attachment
                        ).decode(),
                    }
                )
                continue

            result = ETransportAPI().get_status(
                company_id=picking.company_id,
                document_load_id=current_sending_document.l10n_ro_edi_stock_load_id,
                session=session,
            )

            if "error" in result:
                picking._l10n_ro_edi_stock_create_document_stock_sending_failed(
                    {
                        "message": result["error"],
                        "l10n_ro_edi_stock_load_id": current_sending_document.l10n_ro_edi_stock_load_id,
                        "l10n_ro_edi_stock_uit": current_sending_document.l10n_ro_edi_stock_uit,
                        "raw_xml": base64.b64decode(
                            current_sending_document.attachment
                        ).decode(),
                    }
                )
            else:
                documents_to_delete |= picking._l10n_ro_edi_stock_get_all_documents(
                    ("stock_sent", "stock_sending_failed")
                )
                new_document_data = {
                    "l10n_ro_edi_stock_load_id": current_sending_document.l10n_ro_edi_stock_load_id,
                    "l10n_ro_edi_stock_uit": current_sending_document.l10n_ro_edi_stock_uit,
                    "raw_xml": base64.b64decode(
                        current_sending_document.attachment
                    ).decode(),
                }
                match state := result["content"]["stare"]:
                    case "ok":
                        picking._l10n_ro_edi_stock_create_document_stock_validated(
                            new_document_data
                        )
                    case "in prelucrare":
                        # Document is still being validated
                        picking._l10n_ro_edi_stock_create_document_stock_sent(
                            new_document_data
                        )
                    case "XML cu erori nepreluat de sistem":
                        new_document_data["message"] = _("XML contains errors.")
                        picking._l10n_ro_edi_stock_create_document_stock_sending_failed(
                            new_document_data
                        )
                    case _:
                        picking._l10n_ro_edi_stock_report_unhandled_document_state(
                            state
                        )

        documents_to_delete.unlink()

    ################################################################################
    # Template helpers
    ################################################################################

    @api.model
    def _l10n_ro_edi_stock_get_template_data(self, data: dict):
        """
        Returns the data necessary to render the eTransport template
        """
        commercial_partner = data["partner_id"].commercial_partner_id
        transport_partner = data["transport_partner_id"]
        company_id = data["company_id"]
        scheduled_date = data["scheduled_date"].date()
        name = data["name"]
        commercial_partner_code = None

        if commercial_partner.vat:
            commercial_partner_code = self._l10n_ro_edi_stock_get_cod(
                commercial_partner
            )
        elif self.l10n_ro_edi_stock_operation_type == "30":
            commercial_partner_code = "PF"

        template_data = {
            "send_type": data["send_type"],
            "codDeclarant": self._l10n_ro_edi_stock_get_cod(company_id),
            "refDeclarant": name,
            "notificare": {
                "codTipOperatiune": data["l10n_ro_edi_stock_operation_type"],
                "bunuriTransportate": [
                    {
                        "codScopOperatiune": data["l10n_ro_edi_stock_operation_scope"],
                        "codTarifar": (
                            product.intrastat_code_id.code
                            if "intrastat_code_id" in product._fields
                            else None
                        )
                        or "00000000",
                        "denumireMarfa": product.name,
                        "cantitate": move.product_qty,
                        "codUnitateMasura": move.product_uom_id._get_unece_code(),
                        "greutateNeta": move.weight,
                        "greutateBruta": self._l10n_ro_edi_stock_get_gross_weight(move),
                        "valoareLeiFaraTva": product.list_price,
                    }
                    for move in data["stock_move_ids"]
                    for product in move.product_id
                ],
                "partenerComercial": {
                    "codTara": _eu_country_vat.get(
                        commercial_partner.country_code, commercial_partner.country_code
                    ),
                    "denumire": commercial_partner.name,
                    "cod": commercial_partner_code,
                },
                "dateTransport": {
                    "nrVehicul": data["l10n_ro_edi_stock_vehicle_number"].upper(),
                    "nrRemorca1": data["l10n_ro_edi_stock_trailer_1_number"].upper()
                    if data["l10n_ro_edi_stock_trailer_1_number"]
                    else None,
                    "nrRemorca2": data["l10n_ro_edi_stock_trailer_2_number"].upper()
                    if data["l10n_ro_edi_stock_trailer_2_number"]
                    else None,
                    "codTaraOrgTransport": _eu_country_vat.get(
                        transport_partner.country_code, transport_partner.country_code
                    ),
                    "codOrgTransport": self._l10n_ro_edi_stock_get_cod(
                        transport_partner
                    ),
                    "denumireOrgTransport": transport_partner.name,
                    "dataTransport": scheduled_date,
                },
                "locStartTraseuRutier": {
                    "location_type": data["l10n_ro_edi_stock_start_loc_type"],
                },
                "locFinalTraseuRutier": {
                    "location_type": data["l10n_ro_edi_stock_end_loc_type"],
                },
                "documenteTransport": {
                    "tipDocument": "30",
                    "dataDocument": scheduled_date,
                    "numarDocument": name,
                    "observatii": data["l10n_ro_edi_stock_remarks"],
                },
            },
        }

        if data["send_type"] == "amend":
            template_data["notificare"]["uit"] = data["l10n_ro_edi_stock_document_uit"]

        for loc in ("start", "end"):
            key = "locStartTraseuRutier" if loc == "start" else "locFinalTraseuRutier"

            match template_data["notificare"][key]["location_type"]:
                case "location":
                    match data["picking_type_id"].code:
                        case "outgoing":
                            partner = (
                                data["picking_type_id"].warehouse_id.partner_id
                                if loc == "start"
                                else data["partner_id"]
                            )
                        case "incoming":
                            partner = (
                                data["picking_type_id"].warehouse_id.partner_id
                                if loc == "end"
                                else data["partner_id"]
                            )

                    template_data["notificare"][key]["locatie"] = {
                        "codJudet": STATE_CODES[partner.state_id.code],
                        "denumireLocalitate": partner.city,
                        "denumireStrada": partner.street,
                        "codPostal": partner.zip,
                        "alteInfo": partner.street2,
                    }
                case "bcp":
                    template_data["notificare"][key]["codPtf"] = data[
                        f"l10n_ro_edi_stock_{loc}_bcp"
                    ]
                case "customs":
                    template_data["notificare"][key]["codBirouVamal"] = data[
                        f"l10n_ro_edi_stock_{loc}_customs_office"
                    ]

        return {"data": template_data}

    ################################################################################
    # Misc helpers
    ################################################################################

    @api.model
    def _l10n_ro_edi_stock_get_cod(self, record):
        """
        :return the records vat in the format required by anaf
        """
        return record.vat.upper().replace("RO", "")

    @api.model
    def _l10n_ro_edi_stock_get_gross_weight(self, move):
        """
        :return the gross weight of a stock.move
        """
        return move.weight + sum(
            line.result_package_id.shipping_weight
            for line in move.move_line_ids
            if line.result_package_id
        )

    def _l10n_ro_edi_stock_report_unhandled_document_state(self, state: str):
        """
        Reports an unknown document state from anaf to the user in the chatter
        """
        self.check_singleton()
        self.message_post(
            body=_("Unhandled eTransport document state: %(state)s", state=state)
        )
