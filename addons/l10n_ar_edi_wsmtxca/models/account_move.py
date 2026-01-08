# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
import re
import socket
import xml.etree.ElementTree as etree
from pyafipws.wsaa import WSAA
from pyafipws.wsmtx import WSMTXCA

from odoo import _, models
from odoo.tools.float_utils import float_repr

xWS_DATE_FORMAT = {"wsmtxca": "%Y-%m-%d"}


class AccountMove(models.Model):
    _inherit = "account.move"

    def _handle_afip_error(self, error_msg):
        """Maneja errores de AFIP mostrando un mensaje al usuario"""
        if not self.env.context.get("l10n_ar_invoice_skip_commit"):
            self.env.cr.rollback()
        return error_msg

    def _handle_wsmtxca_exception(self, exception):
        """Maneja excepciones específicas de WSMTXCA"""
        error_msg = str(exception)
        if isinstance(exception, (socket.error, TimeoutError)):
            error_msg = _("Error de conexión con AFIP: %s") % error_msg
        elif isinstance(exception, etree.ParseError):
            error_msg = _("Error al parsear respuesta de AFIP: %s") % error_msg
        return self._handle_afip_error(_("AFIP Exception:\n") + error_msg)

    def _l10n_ar_do_afip_ws_request_cae(self, client, auth, transport):
        self.ensure_one()

        # Primero verificamos si es WSMTXCA para manejar este caso especial
        if self.journal_id.l10n_ar_afip_ws == "wsmtxca":
            try:
                afip_ws = self.journal_id.l10n_ar_afip_ws
                connection = self.company_id._l10n_ar_get_connection(afip_ws)

                wsdl = connection._l10n_ar_get_afip_ws_url(afip_ws, connection.type)

                client, auth = connection._get_client()

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

                # Preparar los datos de la factura
                self.wsmtxca_get_cae_request(wsmtxca_client)

                # Llamar al método autorizarComprobante
                wsmtxca_client.AutorizarComprobante()

                # Procesar la respuesta
                code_due_date = False
                if wsmtxca_client.Resultado in ("A", "O"):  # Aprobado u Observado
                    code_due_date = wsmtxca_client.Vencimiento
                    if code_due_date:
                        code_due_date = datetime.strptime(
                            code_due_date, "%Y/%m/%d"
                        ).date()

                    values = {
                        "l10n_ar_afip_auth_mode": "CAE",
                        "l10n_ar_afip_auth_code": wsmtxca_client.CAE,
                        "l10n_ar_afip_auth_code_due": code_due_date,
                        "l10n_ar_afip_result": wsmtxca_client.Resultado,
                        "l10n_ar_afip_xml_request": wsmtxca_client.XmlRequest,
                        "l10n_ar_afip_xml_response": wsmtxca_client.XmlResponse,
                    }

                    # Guardar los datos en la factura
                    self.sudo().write(values)
                else:
                    # Hubo errores, preparar mensaje de error
                    error_msg = _("AFIP Error: %s") % (
                        wsmtxca_client.ErrMsg or "Error desconocido"
                    )
                    if not self.env.context.get("l10n_ar_invoice_skip_commit"):
                        self.env.cr.rollback()

                    self.sudo().write(
                        {
                            "l10n_ar_afip_xml_request": wsmtxca_client.XmlRequest,
                            "l10n_ar_afip_xml_response": wsmtxca_client.XmlResponse,
                        }
                    )

                    return self._handle_afip_error(error_msg)

            except (socket.error, TimeoutError, etree.ParseError) as e:
                return self._handle_wsmtxca_exception(e)
            except Exception as e:  # noqa: BLE001
                return self._handle_afip_error(_("AFIP Exception: %s") % str(e))

        # Si no es WSMTXCA, llamamos al método original
        return super()._l10n_ar_do_afip_ws_request_cae(client, auth, transport)

    def wsmtxca_get_cae_request(self, client):
        self.ensure_one()

        cbte_nro = self.l10n_latam_document_number

        concepto = self._get_concepto_afip()
        tipo_cbte = int(self.l10n_latam_document_type_id.code)
        punto_vta = int(self.journal_id.l10n_ar_afip_pos_number)

        tipo_doc = (
            80
            if tipo_cbte in [1, 2, 3, 51, 52, 53, 201, 202, 203, 206, 207, 208]
            else 0
        )

        last_id = client.ConsultarUltimoComprobanteAutorizado(tipo_cbte, punto_vta)
        nro_doc = int(last_id) + 1

        invoice_number = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, self.l10n_latam_document_type_id.code
        )["invoice_number"]

        lineas_afip = []

        def procesar_linea(line):
            price_unit = line.price_unit
            discount = line.discount or 0.0
            discount_amount = line.quantity * price_unit - (
                line.quantity * price_unit * (1 - discount / 100)
            )
            qty = line.quantity
            price_unit_with_discount = price_unit * (1 - discount / 100)

            if tipo_cbte in (6, 7, 8):
                alicuota = line.tax_ids[0].amount if line.tax_ids else 0.0
                price_unit_net = price_unit_with_discount / (1 + (alicuota / 100))
            else:
                price_unit_net = price_unit_with_discount

            tax_data = line.tax_ids.compute_all(
                price_unit_net,
                line.currency_id,
                qty,
                product=line.product_id,
                partner=self.partner_id,
            )
            iva = sum(t["amount"] for t in tax_data["taxes"])
            subtotal_sin_iva = price_unit_net * qty

            if not line.tax_ids:
                iva_id = 2
            elif any(t.tax_group_id.l10n_ar_vat_afip_code for t in line.tax_ids):
                iva_id = int(line.tax_ids[0].tax_group_id.l10n_ar_vat_afip_code)
            else:
                iva_id = 3

            importe_item = subtotal_sin_iva + iva

            return {
                "line": line,
                "qty": qty,
                "price_unit": price_unit,
                "discount": discount_amount,
                "iva": iva,
                "importe_item": importe_item,
                "iva_id": iva_id,
                "alicuota": line.tax_ids[0].amount if line.tax_ids else 0.0,
            }

        for line in self.invoice_line_ids:
            data = procesar_linea(line)
            lineas_afip.append(
                {
                    "imp_subtotal": float(data["importe_item"]),
                    "imp_iva": float(data["iva"]),
                    "iva_id": data["iva_id"],
                    "alicuota": data["alicuota"],
                }
            )

        if tipo_cbte in (6, 7, 8):
            importe_gravado = sum(
                item["imp_subtotal"] / (1 + (item["alicuota"] / 100))
                for item in lineas_afip
                if item["iva_id"] in (3, 4, 5, 6)
            )
        else:
            importe_gravado = sum(
                item["imp_subtotal"] - item["imp_iva"]
                for item in lineas_afip
                if item["iva_id"] in (3, 4, 5, 6)
            )

        importe_no_gravado = sum(
            item["imp_subtotal"] for item in lineas_afip if item["iva_id"] == 1
        )

        importe_exento = sum(
            item["imp_subtotal"] for item in lineas_afip if item["iva_id"] == 2
        )

        importe_iva = sum(
            item["imp_iva"] for item in lineas_afip if item["iva_id"] in (3, 4, 5, 6)
        )

        imp_neto = float_repr(importe_gravado, precision_digits=2)
        imp_tot_conc = float_repr(importe_no_gravado, precision_digits=2)
        imp_op_ex = float_repr(importe_exento, precision_digits=2)
        imp_iva = float_repr(importe_iva, precision_digits=2)

        imp_subtotal = float_repr(
            float(imp_tot_conc) + float(imp_neto) + float(imp_op_ex), precision_digits=2
        )
        imp_total = float_repr(float(imp_subtotal) + float(imp_iva), precision_digits=2)

        imp_trib = float_repr(
            sum(
                abs(line.balance)
                for line in self.line_ids
                if line.tax_line_id
                and not line.tax_line_id.tax_group_id.l10n_ar_vat_afip_code
            ),
            precision_digits=2,
        )

        client.CrearFactura(
            concepto=concepto,
            tipo_doc=tipo_doc,
            nro_doc=nro_doc,
            tipo_cbte=tipo_cbte,
            punto_vta=punto_vta,
            cbt_desde=nro_doc,
            cbt_hasta=nro_doc,
            imp_total=imp_total,
            imp_tot_conc=imp_tot_conc,
            imp_neto=imp_neto,
            imp_subtotal=imp_subtotal,
            imp_iva=imp_iva,
            imp_trib=imp_trib,
            imp_op_ex=imp_op_ex,
            fecha_cbte=self.invoice_date.strftime(xWS_DATE_FORMAT["wsmtxca"]),
            moneda_id=self.currency_id.l10n_ar_afip_code or "PES",
            moneda_ctz=float(self.l10n_ar_currency_rate or 1.0),
            observaciones=(self.narration or "")[:1000],
        )

        for data in map(procesar_linea, self.invoice_line_ids):
            line = data["line"]

            barcode = line.product_id.barcode
            if barcode and barcode.isdigit() and len(barcode) in (8, 12, 13):
                cod_mtx = barcode.zfill(13)
            else:
                cod_mtx = ""  # si no es GTIN válido, se envía vacío

            imp_iva = float_repr(float(data["iva"]), precision_digits=2) if data["iva"] else "0.00"

            if data["price_unit"] < 0 or data["qty"] < 0:
                client.AgregarItem(
                    ds=line.name[:50],
                    umed=99,
                    iva_id=data["iva_id"],
                    imp_iva=imp_iva,
                    imp_subtotal=float_repr(
                        float(data["importe_item"]), precision_digits=2
                    ),
                )
            else:
                client.AgregarItem(
                    u_mtx=(
                        line.product_id.uom_id.l10n_ar_afip_code
                        if line.product_id
                        else "7"
                    ),
                    cod_mtx=cod_mtx,
                    codigo=(line.product_id.default_code or "")[:13],
                    ds=line.name[:50],
                    qty=float_repr(float(data["qty"]), precision_digits=2),
                    umed=int(line.product_uom_id.l10n_ar_afip_code or 7),
                    precio=float_repr(float(data["price_unit"]), precision_digits=2),
                    bonif=float_repr(float(data["discount"]), precision_digits=2),
                    iva_id=data["iva_id"],
                    imp_iva=imp_iva,
                    imp_subtotal=float_repr(
                        float(data["importe_item"]), precision_digits=2
                    ),
                )

        # Recalcular los totales de IVA por código desde los ítems enviados
        iva_totales = {}
        for item in lineas_afip:
            iva_id = item["iva_id"]
            if iva_id in (3, 4, 5, 6):
                if iva_id not in iva_totales:
                    iva_totales[iva_id] = {"base": 0.0, "importe": 0.0}
                base = item["imp_subtotal"] / (1 + item["alicuota"] / 100)
                iva_totales[iva_id]["base"] += base
                iva_totales[iva_id]["importe"] += item["imp_iva"]

        for iva_id, vals in iva_totales.items():
            client.AgregarIva(
                iva_id=iva_id,
                base_imp=round(vals["base"], 2),
                importe=round(vals["importe"], 2),
            )

        for tax in self.line_ids.filtered(
            lambda x: x.tax_line_id
            and not x.tax_line_id.tax_group_id.l10n_ar_vat_afip_code
        ):
            client.AgregarTributo(
                tributo_id=tax.tax_line_id.l10n_ar_tribute_afip_code,
                desc=tax.tax_line_id.name[:100],
                base_imp=float(abs(tax.tax_base_amount)),
                alic=float(tax.tax_line_id.amount),
                importe=float(abs(tax.balance)),
            )

        if self.reversed_entry_id:
            # La variable nro no se usa, así que la eliminamos
            int(self.reversed_entry_id.l10n_latam_document_number.replace("-", ""))
            client.AgregarCmpAsoc(
                tipo=int(self.reversed_entry_id.l10n_latam_document_type_id.code),
                pto_vta=int(self.reversed_entry_id.journal_id.l10n_ar_afip_pos_number),
                nro=invoice_number,
                fecha=self.reversed_entry_id.invoice_date.strftime(
                    xWS_DATE_FORMAT["wsmtxca"]
                ),
            )
        else:
            client.factura["cbtes_asoc"] = []

        client.factura["opcionales"] = []

        return {
            "tipo_cbte": tipo_cbte,
            "punto_vta": punto_vta,
            "cbte_nro": cbte_nro,
        }

    def _get_concepto_afip(self):
        """Determina el código de concepto AFIP según el tipo de factura"""
        self.ensure_one()
        # 1: Productos, 2: Servicios, 3: Productos y Servicios
        return 1  # Por defecto Productos, ajustar según necesidad