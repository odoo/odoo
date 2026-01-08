# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from pyafipws.wsaa import WSAA
from pyafipws.wsmtx import WSMTXCA


class L10nArAfipwsConnection(models.Model):
    _inherit = "l10n_ar.afipws.connection"

    @api.model
    def _l10n_ar_get_afip_ws_url(self, afip_ws, environment_type):
        res = super()._l10n_ar_get_afip_ws_url(afip_ws, environment_type)
        if res:
            return res

        ws_data = {
            "wsmtxca": {
                "production": "https://serviciosjava.afip.gob.ar/wsmtxca/services/MTXCAService?wsdl",
                "testing": "https://fwshomo.afip.gov.ar/wsmtxca/services/MTXCAService?wsdl",
            }
        }
        return ws_data.get(afip_ws, {}).get(environment_type)


class L10nArAfipWsConsult(models.TransientModel):
    _inherit = "l10n_ar_afip.ws.consult"

    journal_id = fields.Many2one(
        "account.journal",
        domain="[('l10n_ar_afip_pos_system', 'in', ['RAW_MAW', 'BFEWS', 'FEEWS', 'MTXCA'])]",
        required=True,
    )

    def button_confirm(self):
        if self.journal_id.l10n_ar_afip_pos_system == "MTXCA":
            return self._button_confirm_mtxca()
        return super().button_confirm()

    def _button_confirm_mtxca(self):
        self.ensure_one()
        afip_ws = self.journal_id.l10n_ar_afip_ws

        if not afip_ws:
            raise UserError(
                _("No AFIP WS selected on point of sale %s") % (self.journal_id.name)
            )
        if not self.number:
            raise UserError(_("Please set the number you want to consult"))
       
        if afip_ws == "wsmtxca":
            connection = self.journal_id.company_id._l10n_ar_get_connection(afip_ws)
            wsdl = connection._l10n_ar_get_afip_ws_url(afip_ws, connection.type)

            _, auth = connection._get_client()

            # Crear instancia del cliente WSMTXCA
            wsmtxca_client = WSMTXCA()

            # Configurar conexión (usar WSDL de homologación o producción)
            wsmtxca_client.Conectar(wsdl=wsdl)

            # Obtener ticket de acceso correctamente formateado
            wsaa_client = WSAA()
            
            if not (auth.get("Token") and auth.get("Sign")): # Si _get_client no proveyó Token/Sign
                wsaa_client.Autenticar(
                    "wsmtxca",
                    connection.company_id.l10n_ar_afip_ws_crt, # Usar connection.company_id
                    connection.company_id.l10n_ar_afip_ws_key, # Usar connection.company_id
                    url=connection._l10n_ar_get_afip_ws_url("wsaa", connection.type),
                )
                # Usar el Token y Sign recién obtenidos si WSAA() se usó para autenticar ahora
                wsmtxca_client.Token = wsaa_client.Token
                wsmtxca_client.Sign = wsaa_client.Sign
            else:
                # Usar Token y Sign de auth si ya estaban presentes
                wsmtxca_client.Token = auth["Token"]
                wsmtxca_client.Sign = auth["Sign"]

            # Configurar CUIT (viene de auth, que a su vez lo toma de la compañía)
            wsmtxca_client.Cuit = auth["Cuit"]


            tipo_cbte = self.document_type_id.code
            punto_vta = self.journal_id.l10n_ar_afip_pos_number

            response = wsmtxca_client.ConsultarUltimoComprobanteAutorizado(
                tipo_cbte, punto_vta
            )
            
            if wsmtxca_client.CodigoError:
                 raise UserError(_("Error al consultar último comprobante: %s - %s") % (wsmtxca_client.CodigoError, wsmtxca_client.MsgError))
            raise UserError(_("Últ. comprobante: %s") % response)
       
        return True