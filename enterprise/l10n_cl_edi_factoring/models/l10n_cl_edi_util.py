import logging
from markupsafe import Markup

from odoo.tools.zeep import Client
from odoo import _, models
from odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util import SERVER_URL, TIMEOUT, l10n_cl_edi_retry

_logger = logging.getLogger(__name__)


class L10nClEdiUtilMixin(models.AbstractModel):
    _inherit = 'l10n_cl.edi.util'

    def _l10n_cl_append_sig(self, xml_type, sign, message):
        tag_to_replace = {
            'dteced': Markup('</DTECedido>'),
            'cesion': Markup('</Cesion>'),
            'aec': Markup('</AEC>')
        }
        tag = tag_to_replace.get(xml_type)
        if tag is None:
            return super()._l10n_cl_append_sig(xml_type, sign, message)
        msg1 = message.replace(tag, sign + tag)
        return msg1

    @l10n_cl_edi_retry(logger=_logger)
    def _get_aec_send_status_ws(self, mode, track_id, token):
        client = Client(f'{SERVER_URL[mode]}services/wsRPETCConsulta?WSDL', operation_timeout=TIMEOUT)
        return client.service.getEstEnvio(token, track_id)

    def _get_aec_send_status(self, mode, track_id, digital_signature):
        """
        Request the status of a DTE file sent to the SII.
        """
        token = self._get_token(mode, digital_signature)
        if token is None:
            self._report_connection_err(_('Token cannot be generated. Please try again'))
            return False
        return self._get_aec_send_status_ws(mode, track_id, token)

    def _analyze_aec_sii_result(self, xml_message):
        """ Returns the status of the DTE from the sii_message. """
        status_code = xml_message.findtext('{http://www.sii.cl/XMLSchema}RESP_BODY/ESTADO_ENVIO')
        match status_code:
            case 'EOK':
                return 'accepted'
            case 'UPL' | 'RCP' | 'SOK' | 'FSO' | 'COK' | 'VDC' | 'VCS':
                return 'ask_for_status'
            case _:
                # consider rejected if status is one of these:
                # 'RSC', 'RFS', 'RCR', 'RDC', 'RCS', '1', '2', '6', '7', '8', '9', '10', '-15'],
                return 'rejected'
