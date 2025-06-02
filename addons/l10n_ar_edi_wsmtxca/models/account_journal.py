# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
from odoo import _, api, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_l10n_ar_afip_ws(self):
        result = super()._get_l10n_ar_afip_ws()
        result.append(("wsmtxca", _("Factura Electrónica A/B con detalle")))
        return result

    def _get_l10n_ar_afip_pos_types_selection(self):
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.insert(0, ("MTXCA", _("Factura Electrónica A/B con detalle - Webservice")))
        return res

    @api.depends("l10n_ar_afip_pos_system")
    def _compute_l10n_ar_afip_ws(self):
        custom_mapping = {"MTXCA": "wsmtxca"}

        super()._compute_l10n_ar_afip_ws()

        for rec in self:
            if (
                rec.l10n_ar_afip_pos_system in custom_mapping
                and not rec.l10n_ar_afip_ws
            ):
                rec.l10n_ar_afip_ws = custom_mapping[rec.l10n_ar_afip_pos_system]

    @api.model
    def _get_codes_per_journal_type(self, afip_pos_system):
        usual_codes = ["1", "2", "3", "6", "7", "8", "11", "12", "13"]
        mipyme_codes = ["201", "202", "203", "206", "207", "208", "211", "212", "213"]
        invoice_m_code = ["51", "52", "53"]
        receipt_m_code = ["54"]
        receipt_codes = ["4", "9", "15"]
        if afip_pos_system == "MTXCA":
            return (
                usual_codes
                + receipt_codes
                + invoice_m_code
                + receipt_m_code
                + mipyme_codes
            )
        return super()._get_codes_per_journal_type(afip_pos_system)

    def _l10n_ar_get_afip_last_invoice_number(self, document_type):
        self.ensure_one()
        if self.env.registry.in_test_mode():
            return 0
        # return 0
        # import wdb; wdb.set_trace()

        pos_number = self.l10n_ar_afip_pos_number
        afip_ws = self.l10n_ar_afip_ws
        connection = self.company_id._l10n_ar_get_connection(afip_ws)
        client, auth = connection._get_client()
        last = errors = False

        res = super()._l10n_ar_get_afip_last_invoice_number(document_type)

        if afip_ws == "wsmtxca":

            wsdl = connection._l10n_ar_get_afip_ws_url(afip_ws, connection.type)

            # Crear instancia del cliente WSMTXCA
            from pyafipws.wsaa import WSAA
            from pyafipws.wsmtx import WSMTXCA

            wsmtxca_client = WSMTXCA()

            # Configurar conexión (usar WSDL de homologación o producción)
            wsmtxca_client.Conectar(wsdl=wsdl)

            # Obtener ticket de acceso correctamente formateado
            wsaa_client = WSAA()
            wsaa_client.Autenticar(
                "wsmtxca",
                self.company_id.l10n_ar_afip_ws_crt,
                self.company_id.l10n_ar_afip_ws_key,
            )

            # Configurar autenticación
            wsmtxca_client.Cuit = auth["Cuit"]
            wsmtxca_client.Token = auth["Token"]
            wsmtxca_client.Sign = auth["Sign"]

            # 5. Realizar consulta
            try:
                # response = wsmtxca_client.ConsultarUltimoComprobanteAutorizado(auth, pos_number, document_type.code)
                # response = client.CompUltimoAutorizado()
                response = wsmtxca_client.ConsultarUltimoComprobanteAutorizado(
                    document_type.code, pos_number
                )

                # 1. Primero verificar si tenemos CbteNro directamente
                if hasattr(response, "CbteNro") and response.CbteNro:
                    return response.CbteNro

                # 2. Si no hay CbteNro, verificar la respuesta XML
                if hasattr(response, "XmlResponse") and response.XmlResponse:
                    # Parsear XML para buscar número de comprobante o errores
                    xml_data = self.parse_afip_xml_response(response.XmlResponse)

                    if xml_data.get("numeroComprobante"):
                        return int(xml_data["numeroComprobante"])

                    if xml_data.get("errores"):
                        error_msg = "\n".join(
                            [
                                f"{e['codigo']}: {e['descripcion']}"
                                for e in xml_data["errores"]
                            ]
                        )
                        raise UserError(_(f"Error AFIP:\n{error_msg}"))

                # 3. Si no encontramos nada, devolver 0 (para nuevo punto de venta)
                return 0

            except Exception as e:
                raise UserError(_("Error en la consulta a AFIP: %s") % str(e))

        return res

    def parse_afip_xml_response(self, xml_response):
        """Parsea la respuesta XML de AFIP y extrae datos relevantes"""
        try:
            result = {"errores": [], "numeroComprobante": None}

            # Decodificar si es necesario
            xml_str = (
                xml_response.decode("utf-8")
                if isinstance(xml_response, bytes)
                else xml_response
            )
            root = etree.fromstring(xml_str)

            # Namespace del XML
            ns = {"ns1": "http://impl.service.wsmtxca.afip.gov.ar/service/"}

            # Buscar número de comprobante
            nro_node = root.xpath("//ns1:numeroComprobante", namespaces=ns)
            if nro_node:
                result["numeroComprobante"] = nro_node[0].text

            # Buscar errores
            for error in root.xpath(
                "//ns1:arrayErrores/ns1:codigoDescripcion", namespaces=ns
            ):
                result["errores"].append(
                    {
                        "codigo": error.find("ns1:codigo", namespaces=ns).text,
                        "descripcion": error.find(
                            "ns1:descripcion", namespaces=ns
                        ).text,
                    }
                )

            return result

        except Exception as e:
            return {"errores": [{"codigo": "PARSE_ERROR", "descripcion": str(e)}]}

    # TODO - este me deja dudas
    def l10n_ar_check_afip_pos_number(self):
        self.ensure_one()
        connection = self.company_id._l10n_ar_get_connection(self.l10n_ar_afip_ws)
        client, auth = connection._get_client()

        super().l10n_ar_check_afip_pos_number()

        if self.l10n_ar_afip_ws == "wsmtxca":
            client.service.ConsultarPuntosVentaCAE(auth)
