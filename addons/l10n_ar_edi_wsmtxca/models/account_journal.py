# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
from odoo import _, api, models
from odoo.exceptions import UserError
import socket
import xml.etree.ElementTree

from pyafipws.wsaa import WSAA
from pyafipws.wsmtx import WSMTXCA


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

    def _handle_afip_error(self, error_msg):
        """Maneja errores de AFIP mostrando un mensaje al usuario"""
        raise UserError(_("Error AFIP: %s") % error_msg)

    def _handle_wsmtxca_exception(self, exception):
        """Maneja excepciones específicas de WSMTXCA"""
        error_msg = str(exception)
        if isinstance(exception, (socket.error, TimeoutError)):
            error_msg = _("Error de conexión con AFIP: %s") % error_msg
        elif isinstance(exception, xml.etree.ElementTree.ParseError):
            error_msg = _("Error al parsear respuesta de AFIP: %s") % error_msg
        self._handle_afip_error(error_msg)

    def _l10n_ar_get_afip_last_invoice_number(self, document_type):
        self.ensure_one()
        if self.env.registry.in_test_mode():
            return 0
        
        pos_number = self.l10n_ar_afip_pos_number
        afip_ws = self.l10n_ar_afip_ws
        connection = self.company_id._l10n_ar_get_connection(afip_ws)
        _, auth = connection._get_client()
        
        res = super()._l10n_ar_get_afip_last_invoice_number(document_type)

        if afip_ws == "wsmtxca":
            wsdl = connection._l10n_ar_get_afip_ws_url(afip_ws, connection.type)
            wsmtxca_client = WSMTXCA()

            try:
                # Configurar conexión
                wsmtxca_client.Conectar(wsdl=wsdl)

                # Obtener ticket de acceso
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

                # Realizar consulta
                response = wsmtxca_client.ConsultarUltimoComprobanteAutorizado(
                    document_type.code, pos_number
                )

                # 1. Verificar CbteNro directamente
                if hasattr(response, "CbteNro") and response.CbteNro:
                    return response.CbteNro

                # 2. Verificar respuesta XML
                if hasattr(response, "XmlResponse") and response.XmlResponse:
                    xml_data = self.parse_afip_xml_response(response.XmlResponse)

                    if xml_data.get("numeroComprobante"):
                        return int(xml_data["numeroComprobante"])

                    if xml_data.get("errores"):
                        error_msg = "\n".join(
                            [f"{e['codigo']}: {e['descripcion']}" for e in xml_data["errores"]]
                        )
                        self._handle_afip_error(error_msg)

                # 3. Si no encontramos nada, devolver 0
                return 0

            except (socket.error, TimeoutError, xml.etree.ElementTree.ParseError) as e:
                self._handle_wsmtxca_exception(e)
            except Exception as e:  # noqa: BLE001
                # Solo para errores realmente inesperados que no podemos manejar específicamente
                self._handle_afip_error(_("Error inesperado en la consulta a AFIP: %s") % str(e))

        return res

    def parse_afip_xml_response(self, xml_response):
        """Parsea la respuesta XML de AFIP y extrae datos relevantes"""
        result = {"errores": [], "numeroComprobante": None}

        try:
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
                        "descripcion": error.find("ns1:descripcion", namespaces=ns).text,
                    }
                )

        except (etree.ParseError, AttributeError, ValueError) as e:
            result["errores"].append({"codigo": "PARSE_ERROR", "descripcion": str(e)})
        
        return result

    def l10n_ar_check_afip_pos_number(self):
        self.ensure_one()
        connection = self.company_id._l10n_ar_get_connection(self.l10n_ar_afip_ws)
        client, auth = connection._get_client()

        super().l10n_ar_check_afip_pos_number()

        if self.l10n_ar_afip_ws == "wsmtxca":
            client.service.ConsultarPuntosVentaCAE(auth)
