# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

        connection = self.journal_id.company_id._l10n_ar_get_connection(afip_ws)
        client, auth = connection._get_client()

        res = error = False
        # We need to call a different method for every webservice type and assemble the returned errors if they exist
        if afip_ws == "wsmtxca":
            afip_ws = self.journal_id.l10n_ar_afip_ws
            connection = self.journal_id.company_id._l10n_ar_get_connection(afip_ws)

            wsdl = connection._l10n_ar_get_afip_ws_url(afip_ws, connection.type)

            client, auth = connection._get_client()

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
                self.journal_id.company_id.l10n_ar_afip_ws_crt,
                self.journal_id.company_id.l10n_ar_afip_ws_key,
            )

            # Configurar autenticación
            wsmtxca_client.Cuit = auth["Cuit"]
            wsmtxca_client.Token = auth["Token"]
            wsmtxca_client.Sign = auth["Sign"]

            tipo_cbte = self.document_type_id.code
            punto_vta = self.journal_id.l10n_ar_afip_pos_number

            response = wsmtxca_client.ConsultarUltimoComprobanteAutorizado(
                tipo_cbte, punto_vta
            )
            raise UserError(_("Ult. comprobante") + response)
