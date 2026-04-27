import base64

from lxml import etree
from markupsafe import Markup

from odoo.addons.l10n_uy_edi.models.account_move import format_float
from odoo.exceptions import UserError
from odoo.tools import html2plaintext
from odoo.tools.xml_utils import cleanup_xml_node

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _description = "Stock Picking - Delivery Guide (Uruguay)"

    l10n_latam_document_type_id = fields.Many2one(
        comodel_name="l10n_latam.document.type",
        string="Document Type (UY)",
        compute="_compute_l10n_latam_document_type_id",
        readonly=False,
        store=True,
    )
    l10n_latam_document_number = fields.Char(string="Document Number (UY)", readonly=True, copy=False)
    l10n_latam_available_document_type_ids = fields.Many2many(
        "l10n_latam.document.type", compute="_compute_l10n_latam_available_document_types"
    )

    l10n_uy_edi_document_id = fields.Many2one("l10n_uy_edi.document", string="Uruguay E-Remito CFE", copy=False)
    l10n_uy_edi_cfe_uuid = fields.Char(related="l10n_uy_edi_document_id.uuid")
    l10n_uy_edi_cfe_state = fields.Selection(related="l10n_uy_edi_document_id.state", store=True)
    l10n_uy_edi_error = fields.Text(related="l10n_uy_edi_document_id.message")
    l10n_uy_is_cfe = fields.Boolean(
        compute="_compute_l10n_uy_is_cfe",
        help="Technical field to know if it's an electronic document or not and use it in the view to show or require certain fields.",
    )
    l10n_uy_edi_addenda_ids = fields.Many2many(
        "l10n_uy_edi.addenda",
        string="Addenda & Disclosure",
        domain="[('type', '=', 'addenda'), ('company_id', 'in', [company_id, False])]",
        help="Addendas and Mandatory Disclosure to add on the CFE. They can be added either to the issuer, receiver,"
        " cfe doc additional info section or to the addenda section. However, the item type should not be set in"
        " this field; instead, it should be specified in the invoice lines.",
        ondelete="restrict",
    )

    l10n_uy_edi_reference = fields.Many2one(
        "l10n_uy_edi.document",
        string="EDI Reference",
        domain="[('picking_id', '!=', False), ('picking_id.partner_id', '=', partner_id), ('state', 'in', ['accepted', 'received', 'rejected'])]",
        help="If filled with a reference, means the Delivery Guide is a correction of the selected document. "
             "Only documents from the same partner can be referenced.",
        ondelete="set null",
    )

    l10n_uy_edi_operation_type = fields.Selection(
        [("1", "Sale"), ("2", "Internal Transfer")],
        string="Type of Operation (UY)",
        readonly=False,
        store=True,
        copy=False,
    )

    l10n_uy_edi_pdf_report_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="PDF Attachment",
        compute=lambda self: self._compute_linked_attachment_id("l10n_uy_edi_pdf_report_id", "l10n_uy_edi_pdf_report_file"),
        depends=["l10n_uy_edi_pdf_report_file"],
    )
    l10n_uy_edi_pdf_report_file = fields.Binary(
        attachment=True,
        string="PDF File",
        copy=False,
    )

    # Compute methods
    @api.depends("l10n_uy_edi_operation_type", "l10n_latam_available_document_type_ids")
    def _compute_l10n_latam_document_type_id(self):
        for picking in self:
            if picking.l10n_uy_edi_operation_type:
                picking.l10n_latam_document_type_id = picking.l10n_latam_available_document_type_ids.filtered(
                    lambda x: x.code == "181"
                )  # e-Delivery Guide Document
            else:
                picking.l10n_latam_document_type_id = False

    @api.depends("l10n_latam_document_number")
    def _compute_display_name(self):
        """Display: 'Stock Picking Internal Sequence : Delivery Guide Number (if defined)'"""
        super()._compute_display_name()
        for picking in self.filtered(lambda x: x.l10n_latam_document_number):
            picking.display_name = picking.name + ": (%s %s)" % (
                picking.l10n_latam_document_type_id.doc_code_prefix,
                picking.l10n_latam_document_number,
            )

    @api.depends("country_code", "picking_type_code", "l10n_latam_document_type_id")
    def _compute_l10n_uy_is_cfe(self):
        for picking in self:
            picking.l10n_uy_is_cfe = (
                picking.country_code == "UY"
                and picking.picking_type_code == "outgoing"
                and picking.l10n_latam_document_type_id.code == "181"
            )

    @api.depends("partner_id", "company_id", "picking_type_code")
    def _compute_l10n_latam_available_document_types(self):
        uy_pickings = self.filtered(lambda x: x.country_code == "UY" and x.picking_type_code == "outgoing")
        uy_pickings.l10n_latam_available_document_type_ids = self.env["l10n_latam.document.type"].search(
            self._get_l10n_latam_documents_domain()
        )
        (self - uy_pickings).l10n_latam_available_document_type_ids = False

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        """Helper to retrieve Attachment from Binary fields
        This is needed because fields.Many2one('ir.attachment') makes all
        attachments available to the user.
        """
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids), ("res_field", "=", binary_field)]
        )
        move_vals = {att.res_id: att for att in attachments}
        for move in self:
            move[attachment_field] = move_vals.get(move._origin.id, False)

    # Buttons

    def action_cancel(self):
        """The delivery guide can not be modified once it has been accepted by DGI"""
        if self.filtered(
            lambda x: x.l10n_uy_is_cfe and x.l10n_uy_edi_cfe_state in ["accepted", "rejected", "received"]
        ):
            raise UserError(self.env._("You can not cancel a Delivery Guide that has already been processed by DGI"))
        return super().action_cancel()

    def l10n_uy_edi_action_update_dgi_state(self):
        self.ensure_one()
        self.l10n_uy_edi_document_id.action_update_dgi_state()

    def l10n_uy_edi_create_delivery_guide(self):
        """ Create the e-Remito (Delivery Guide) CFE and send it to DGI.
        The e-Remito has the following parts in the XML file:
        A. Encabezado
        B. Detalle de los productos
        C. Subtotales Informativos (optional)
        F. Informacion de Referencia (conditional)
        """
        # Filter only e-remitos
        pickings = self.filtered(
            lambda x: x.country_code == "UY"
            and x.picking_type_code == "outgoing"
            and x.l10n_latam_document_type_id
            and int(x.l10n_latam_document_type_id.code) > 0
            and x.l10n_uy_edi_cfe_state not in ["accepted", "rejected", "received"]
        )

        if not pickings:
            return

        # Send invoices to DGI and get the return info
        msg = ""
        self.env['res.company']._with_locked_records(pickings)
        for picking in pickings:
            edi_doc = self.env["l10n_uy_edi.document"].create(
                {
                    "picking_id": picking.id,
                    "uuid": self.env["l10n_uy_edi.document"]._get_picking_uuid(picking),
                }
            )
            picking.l10n_uy_edi_document_id = edi_doc

            if picking.company_id.l10n_uy_edi_ucfe_env == "demo":
                attachments = picking._l10n_uy_edi_dummy_validation()
                msg = self.env._(
                    "This CFE has been generated in DEMO Mode. It is considered"
                    ' as accepted and it won"t be sent to DGI.'
                )
            else:
                request_data = picking._l10n_uy_stock_prepare_req_data()
                result = edi_doc._send_dgi(request_data)
                edi_doc._update_cfe_state(result)

                response = result.get("response")

                if edi_doc.message:
                    picking.message_post(
                        body=Markup("<font style='color:Tomato;'><strong>{}:</strong></font> <i>{}</<i>").format(
                            ("ERROR"), edi_doc.message
                        )
                    )
                elif edi_doc.state in ["received", "accepted"]:
                    # If everything is ok, save the return information
                    picking.l10n_latam_document_number = response.findtext(".//{*}Serie") + "%07d" % int(
                        response.findtext(".//{*}NumeroCfe")
                    )

                    msg = response.findtext(".//{*}MensajeRta", "")
                    msg += self.env._("The electronic invoice was created successfully")

                if response is not None:
                    attachments = picking._l10n_uy_edi_update_xml_and_pdf_file(response)
                else:
                    attachments = None
                picking.message_post(
                    body=msg,
                    attachment_ids=attachments.ids if attachments else False,
            )

    def l10n_uy_edi_action_download_preview_xml(self):
        if self.l10n_uy_edi_document_id.attachment_id:
            return self.l10n_uy_edi_document_id.action_download_file()

    # Helpers

    def _get_l10n_latam_documents_domain(self):
        codes = self._l10n_uy_get_delivery_guide_codes()
        return [
            ("code", "in", codes),
            ("code", "!=", "0"),
            ("active", "=", True),
            ("internal_type", "=", "stock_picking"),
        ]

    def _l10n_uy_edi_update_xml_and_pdf_file(self, response):
        """Cleans up the PDF and XML fields. Creates new ones with the response"""
        self.ensure_one()
        res_files = self.env["ir.attachment"]
        edi_doc = self.l10n_uy_edi_document_id
        edi_doc._compute_from_origin()

        self.l10n_uy_edi_pdf_report_id.res_field = False
        edi_doc.attachment_id.res_field = False

        xml_content = response.findtext(".//{*}XmlCfeFirmado")
        if xml_content:
            res_files = self.env["ir.attachment"].create(
                {
                    "res_model": "l10n_uy_edi.document",
                    "res_field": "attachment_file",
                    "res_id": edi_doc.id,
                    "name": edi_doc._get_xml_attachment_name(),
                    "type": "binary",
                    "datas": base64.b64encode(
                        xml_content.encode()
                        if self.l10n_uy_edi_cfe_state in ["received", "accepted"]
                        else self._l10n_uy_edi_get_xml_content().encode()
                    ),
                }
            )

            edi_doc.invalidate_recordset(["attachment_id", "attachment_file"])

            # If the record has been posted automatically print and attach the legal report to the record.
            if self.l10n_uy_edi_cfe_state and self.l10n_uy_edi_cfe_state != "error":
                pdf_result = self._l10n_uy_edi_get_pdf()
                if pdf_file := pdf_result.get("pdf_file"):
                    # make sure latest PDF shows to the right of the chatter
                    pdf_file.register_as_main_attachment(force=True)
                    self.invalidate_recordset(fnames=["l10n_uy_edi_pdf_report_id", "l10n_uy_edi_pdf_report_file"])
                    res_files |= pdf_file
                if errors := pdf_result.get("errors"):
                    msg = self.env._("Error getting the PDF file: %s", errors)
                    self.l10n_uy_edi_error = (self.l10n_uy_edi_error or "") + msg
                    self.message_post(body=msg)
        else:
            self._l10n_uy_edi_get_preview_xml()
        return res_files

    def _l10n_uy_edi_dummy_validation(self):
        # Extends l10n_uy_edi
        """ When we want to skip DGI and validate only in Odoo.
        Change move_id with picking_id"""
        edi_doc = self.l10n_uy_edi_document_id
        edi_doc.state = "accepted"
        self.write(
            {
                "l10n_latam_document_number": "DE%07d" % (edi_doc.picking_id.id),
            }
        )

        return self._l10n_uy_edi_get_preview_xml()

    def _l10n_uy_edi_get_preview_xml(self):
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        edi_doc.attachment_id.res_field = False
        xml_file = self.env["ir.attachment"].create(
            {
                "res_model": "l10n_uy_edi.document",
                "res_field": "attachment_file",
                "res_id": edi_doc.id,
                "name": edi_doc._get_xml_attachment_name(),
                "type": "binary",
                "datas": base64.b64encode(self._l10n_uy_edi_get_xml_content().encode()),
            }
        )
        edi_doc.invalidate_recordset(["attachment_id", "attachment_file"])
        return xml_file

    def _l10n_uy_edi_get_pdf(self):
        """Calls endpoint to get PDF file from Uruware (Standard Representation)
        return: dictionary with {"errors": str(): "pdf_file"attachment object }"""
        res = {}
        result = self.l10n_uy_edi_document_id._get_pdf()
        if file_content := result.get("file_content"):
            pdf_file = self.env["ir.attachment"].create(
                {
                    "res_model": "stock.picking",
                    "res_id": self.id,
                    "res_field": "l10n_uy_edi_pdf_report_file",
                    "name": self.l10n_uy_edi_document_id._get_xml_attachment_name().replace(".xml", ".pdf"),
                    "type": "binary",
                    "datas": file_content,
                }
            )
            res["pdf_file"] = pdf_file

        return res

    def _l10n_uy_edi_get_addenda(self):
        """Returns a string with the addenda of the e-Rem"""
        addenda = ""
        if self.l10n_uy_edi_reference:
            addenda = f"Correction of {self.l10n_uy_edi_reference.picking_id.name}"

        addenda += self.l10n_uy_edi_document_id._get_legends("addenda", self)
        if self.origin:
            addenda += "\n\nOrigin: %s" % self.origin
        if self.note:
            addenda += "\n\n%s" % html2plaintext(self.note)
        return addenda.strip()

    def _l10n_uy_get_delivery_guide_codes(self):
        """Returns a list of the available document type codes for stock picking"""
        return ["0", "181"]

    # Prepare XML values

    def _l10n_uy_stock_prepare_req_data(self):
        """Creates a dictionary with the request to generate the EDI document"""
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        xml_content = self._l10n_uy_edi_get_xml_content()
        req_data = {
            "Uuid": edi_doc.uuid,
            "TipoCfe": int(self.l10n_latam_document_type_id.code),
            "HoraReq": edi_doc.request_datetime.strftime("%H%M%S"),
            "FechaReq": edi_doc.request_datetime.date().strftime("%Y%m%d"),
            "CfeXmlOTexto": xml_content,
        }

        if addenda := self._l10n_uy_edi_get_addenda():
            req_data["Adenda"] = addenda
        return req_data

    def _l10n_uy_edi_get_cfe_lines(self):
        self.ensure_one()
        return self.move_line_ids

    def _l10n_uy_edi_get_xml_content(self):
        """Creates the CFE xml structure and validate it
        Returns a string with the xml content to send to DGI"""
        self.ensure_one()
        template_name = "l10n_uy_edi_stock." + self.l10n_uy_edi_document_id._get_cfe_picking_tag(self) + "_template"
        values = {
            "cfe": self,
            "res_model": self._name,
            "IdDoc": self._l10n_uy_stock_cfe_A_iddoc(),
            "emisor": self._l10n_uy_stock_cfe_A_issuer(),
            "receptor": self._l10n_uy_stock_cfe_A_receptor(),
            "totals_detail": self._l10n_uy_stock_cfe_A_totals(),
            "item_detail": self._l10n_uy_stock_cfe_B_details(),
            "referencia_lines": self._l10n_uy_edi_cfe_F_reference(),
            "format_float": format_float,
        }
        cfe = self.env["ir.qweb"]._render(template_name, values=values)
        return etree.tostring(cleanup_xml_node(cfe)).decode()

    def _l10n_uy_stock_cfe_A_iddoc(self):
        """Prepares XML Section A (Encabezado / Identificacion del Documento)"""
        values = {
            "TipoCFE": self.l10n_latam_document_type_id.code,
            "FchEmis": self.scheduled_date.date(),
            "TipoTraslado": self.l10n_uy_edi_operation_type,  # A5
        }

        empty_values = {}.fromkeys(
            ["MntBruto", "FmaPago", "FchVenc", "ClauVenta", "InfoAdicionalDoc", "ModVenta", "ViaTransp"], None
        )
        values.update(empty_values)
        return values

    def _l10n_uy_stock_cfe_A_issuer(self):
        """Prepares XML Section A (Encabezado / Issuer)"""
        return {
            "RUCEmisor": self.company_id.vat,
            "RznSoc": self.company_id.name[:150],
            "CdgDGISucur": self.company_id.l10n_uy_edi_branch_code,
            "DomFiscal": self.company_id.partner_id._l10n_uy_edi_get_fiscal_address(),
            "Ciudad": (self.company_id.city or "")[:30] or None,
            "Departamento": (self.company_id.state_id.name or "")[:30] or None,
            "InfoAdicionalEmisor": self.l10n_uy_edi_document_id._get_legends("issuer", self) or None,
        }

    def _l10n_uy_stock_cfe_A_receptor(self):
        """Prepares XML Section A (Encabezado / Receptor)"""
        self.ensure_one()
        doc_type = self.partner_id._l10n_uy_edi_get_doc_type()
        values = {
            "TipoDocRecep": doc_type or None,  # A60
            "CodPaisRecep": self.partner_id.country_id.code or ("UY" if doc_type in [2, 3] else "99"),  # A61
            "DocRecep": self.partner_id.vat if doc_type in [1, 2, 3] else None,  # A62
            "DocRecepExt": self.partner_id.vat if doc_type not in [1, 2, 3] else None,  # A62.1
            "RznSocRecep": self.partner_id.name[:150] or None,  # A63
            "DirRecep": self.partner_id._l10n_uy_edi_get_fiscal_address() or None,  # A64
            "CiudadRecep": self.partner_id.city and self.partner_id.city[:30] or None,  # A65
            "DeptoRecep": self.partner_id.state_id and self.partner_id.state_id.name[:30] or None,  # A66
            "PaisRecep": self.partner_id.country_id and self.partner_id.country_id.name or None,  # A66.1
            "InfoAdicional": self.l10n_uy_edi_document_id._get_legends("receiver", self) or None,  # A68
            "LugarDestEnt": self._l10n_uy_edi_get_delivery_address() or None,  # A69
        }
        empty_values = {}.fromkeys(["CompraID"], None)
        values.update(empty_values)
        return values

    def _l10n_uy_edi_get_delivery_address(self):
        """Gets the delivery address of the picking, if it exists"""
        self.ensure_one()
        if self.partner_id.type == "delivery":
            return self.partner_id.contact_address_complete

    def _l10n_uy_stock_cfe_A_totals(self):
        """Prepares XML Section C (Subtotales Informativos)"""
        self.ensure_one()
        lines = self._l10n_uy_edi_get_cfe_lines()
        res = {
            "CantLinDet": len(lines),  # A126
        }

        empty_values = {}.fromkeys(
            [
                "MntNoGrv",
                "MntNetoIvaTasaMin",
                "MntNetoIVATasaBasica",
                "MntNetoIVAOtra",
                "IVATasaMin",
                "IVATasaBasica",
                "MntIVATasaMin",
                "MntIVATasaBasica",
                "MntIVAOtra",
                "MntTotal",
                "MontoNF",
                "MntPagar",
                "TpoMoneda",
                "TpoCambio",
                "MntExpoyAsim",
            ],
            None,
        )
        res.update(empty_values)
        return res

    def _l10n_uy_stock_cfe_B_details(self):
        """Prepares XML Section B (Detalles)"""
        self.ensure_one()
        res = []

        for k, line in enumerate(self.move_line_ids, start=1):
            temp = {
                "NroLinDet": k,  # B1
                "IndFact": 8 if self.l10n_uy_edi_reference else None,  # B4
                "NomItem": line.display_name,  # B7
                "DscItem": line.description_picking
                if line.description_picking and line.description_picking != line.display_name
                else None,  # B8
                "Cantidad": line.quantity,  # B9
                "UniMed": line.product_uom_id.name[:4] if line.product_uom_id else "N/A",  # B10
            }
            empty_values = {}.fromkeys(
                [
                    "PrecioUnitario",
                    "DescuentoPct",
                    "DescuentoMonto",
                    "MontoItem",
                ],
                None,
            )
            temp.update(empty_values)
            res.append(temp)

        return res

    def _l10n_uy_edi_cfe_F_reference(self):
        """Prepares XML Section F (Referencias)"""
        self.ensure_one()
        res = []
        if self.l10n_uy_edi_reference:
            referenced_doc = self.l10n_uy_edi_reference
            cfe_serie, cfe_number = self.l10n_uy_edi_document_id._get_doc_parts(referenced_doc)
            res.append(
                {
                    "NroLinRef": 1,  # F1
                    "TpoDocRef": int(referenced_doc.l10n_latam_document_type_id.code),  # F3
                    "Serie": cfe_serie,  # F4
                    "NroCFERef": cfe_number,  # F5
                }
            )
        return res
