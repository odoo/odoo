import base64

import markupsafe

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_ro_edi_stock.models.etransport_api import ETransportAPI


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # Document fields
    l10n_ro_edi_stock_document_ids = fields.One2many(
        comodel_name="l10n_ro_edi.document",
        inverse_name="batch_id",
    )

    def _l10n_ro_edi_stock_is_shipped(self) -> bool:
        return self.state != "draft"

    ################################################################################
    # Validation methods
    ################################################################################

    def action_done(self):
        # EXTENDS 'stock_picking_batch'
        self.check_singleton()
        if not self.l10n_ro_edi_stock_enable:
            return super().action_done()
        self._check_company()

        self.picking_ids.with_context(
            l10n_ro_edi_stock_validate_carrier=True
        )._l10n_ro_edi_stock_check_carrier()

        # Carrier should be the same on all pickings
        first_carrier = self.picking_ids[0].carrier_id
        if any(picking.carrier_id != first_carrier for picking in self.picking_ids):
            raise UserError(
                _("All Pickings in a Batch Transfer should have the same Carrier")
            )

        # Commercial partner should be the same on all pickings
        first_commercial_partner = self.picking_ids[0].partner_id.commercial_partner_id
        if any(
            picking.partner_id.commercial_partner_id != first_commercial_partner
            for picking in self.picking_ids
        ):
            raise UserError(
                _(
                    "All Pickings in a Batch Transfer should have the same Commercial Partner"
                )
            )

        return super().action_done()

    def _l10n_ro_edi_stock_get_fetch_data_errors(self, errors=None):
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
        self.check_singleton()

        send_type = self.env.context.get("l10n_ro_edi_stock_send_type", "send")
        self._l10n_ro_edi_stock_send_etransport_document(send_type=send_type)

    def action_l10n_ro_edi_stock_fetch_status(self):
        self._l10n_ro_edi_stock_update_document_status()

    ################################################################################
    # Document Helpers
    ################################################################################

    def _l10n_ro_edi_stock_create_document_stock_sent(self, values: dict[str, object]):
        self.check_singleton()
        return self.env["l10n_ro_edi.document"].create(
            {
                "batch_id": self.id,
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
                "batch_id": self.id,
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
                "batch_id": self.id,
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
            "partner_id": self.picking_ids[0].partner_id,
            "transport_partner_id": self.picking_ids[
                0
            ].carrier_id.l10n_ro_edi_stock_partner_id,
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

        if errors := self.env["stock.picking"]._l10n_ro_edi_stock_get_data_errors(
            data=data
        ):
            self._l10n_ro_edi_stock_get_all_documents("stock_sending_failed").unlink()
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
            values=self.env["stock.picking"]._l10n_ro_edi_stock_get_template_data(
                data=data
            ),
        )

        result = ETransportAPI().upload_data(company_id=self.company_id, data=raw_xml)

        if "error" in result:
            self._l10n_ro_edi_stock_get_all_documents("stock_sending_failed").unlink()
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
                raw_xml = base64.b64decode(last_validated.attachment).decode()

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
        to_fetch = self.filtered(lambda b: b.l10n_ro_edi_stock_state == "stock_sent")

        for batch in to_fetch:
            current_sending_document = batch.l10n_ro_edi_stock_document_ids.filtered(
                lambda doc: doc.state == "stock_sent"
            )[0]

            if errors := batch._l10n_ro_edi_stock_get_fetch_data_errors():
                documents_to_delete |= batch._l10n_ro_edi_stock_get_all_documents(
                    "stock_sending_failed"
                )
                batch._l10n_ro_edi_stock_create_document_stock_sending_failed(
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
                company_id=batch.company_id,
                document_load_id=current_sending_document.l10n_ro_edi_stock_load_id,
                session=session,
            )

            if "error" in result:
                documents_to_delete |= batch._l10n_ro_edi_stock_get_all_documents(
                    "stock_sending_failed"
                )
                batch._l10n_ro_edi_stock_create_document_stock_sending_failed(
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
                documents_to_delete |= batch._l10n_ro_edi_stock_get_all_documents(
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
                        batch._l10n_ro_edi_stock_create_document_stock_validated(
                            new_document_data
                        )
                    case "in prelucrare":
                        # Document is still being validated
                        batch._l10n_ro_edi_stock_create_document_stock_sent(
                            new_document_data
                        )
                    case "XML cu erori nepreluat de sistem":
                        new_document_data["message"] = _("XML contains errors.")
                        batch._l10n_ro_edi_stock_create_document_stock_sending_failed(
                            new_document_data
                        )
                    case _:
                        batch._l10n_ro_edi_stock_report_unhandled_document_state(state)

        documents_to_delete.unlink()

    ################################################################################
    # Misc helpers
    ################################################################################

    def _l10n_ro_edi_stock_report_unhandled_document_state(self, state: str):
        self.check_singleton()
        self.message_post(
            body=_("Unhandled eTransport document state: %(state)s", state=state)
        )
