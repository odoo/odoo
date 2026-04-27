import base64
import logging
import requests

from datetime import datetime, timezone
from json import JSONDecodeError
from requests import RequestException

_logger = logging.getLogger(__name__)


def _l10n_gt_edi_send_to_sat(company, xml_data, identification_key):
    """
    Send XML data to the Guatemalan SAT.

    The SAT will then send back a response dictionary with the following format:
    {
        'resultado': <boolean: True if success; False otherwise>,
        'fecha': <string>,
        'origen': <string>,
        'descripcion': <string>,
        'control_emision': {'Saldo': <int>, 'Creditos': <int>},
        'alertas_infile': <boolean>,
        'descripcion_alertas_infile': <list>,
        'alertas_sat': <boolean>,
        'descripcion_alertas_sat': <list>,
        'cantidad_errores': <int>,
        'descripcion_errores': <list[ErrorDict]: list of error dictionaries>,
        'informacion_adicional': <string>,
        'serie': <string>,
        'uuid': <string>,
        'numero': <int>,
        'xml_certificado': <string: the successful certificate; empty if not successful>,
    }

    On error, the error dictionary <ErrorDict> will look like the following:
    {
        'resultado': <boolean>,
        'fuente': <string>,
        'categoria': <string_digits>,
        'numeral': <string_digits>,
        'validacion': <string_digits>,
        'mensaje_error': <string: the error message>,
    }

    :param res.company company:
    :param str | bytes xml_data:
    :param str identification_key:
    :return: a dictionary with the following format:
    if error: { 'errors': <list[str]: list of error messages> }
    if success: {
        'certificate': <bytes | string: the successful XML data containing the certificate>,
        'uuid': <string>,
        'series': <string>,
        'serial_number': <string>,
    }
    """
    response = None

    if company.l10n_gt_edi_service_provider == 'demo':
        # Do not send to Infile on demo. Mock a successful result instead.
        return {
            'certificate': f"<!-- Demo sending successful -->\n{xml_data}",
            'uuid': 'DEMO',
            'series': 'DEMO',
            'serial_number': 'DEMO',
            'certification_date': 'DEMO',
        }
    try:
        response = requests.post(
            url="https://certificador.feel.com.gt/fel/procesounificado/transaccion/v2/xml",
            headers={
                'UsuarioFirma': company.l10n_gt_edi_ws_prefix,
                'LlaveFirma': company.l10n_gt_edi_infile_token,
                'UsuarioApi': company.l10n_gt_edi_ws_prefix,
                'LlaveApi': company.l10n_gt_edi_infile_key,
                'identificador': f"ODOO_{identification_key}_{datetime.now(timezone.utc):%Y_%m_%d_%H_%M_%S_%f}",
            },
            data=xml_data,
            timeout=60,
        )
        response.raise_for_status()
        res_data = response.json()
    except (RequestException, JSONDecodeError) as err:
        _logger.error("[l10n_gt_edi] Sending request to SAT failed: %s\nResponse content: %s", err, response and response.content)
        return {'errors': [str(err)]}

    if not res_data['resultado']:
        errors = []
        for error_vals in res_data['descripcion_errores']:
            errors.append(error_vals['mensaje_error'])
        return {'errors': errors}
    else:  # successful result
        return {
            'certificate': base64.b64decode(res_data['xml_certificado']).decode(),
            'uuid': res_data['uuid'],
            'series': res_data['serie'],
            'serial_number': str(res_data['numero']),
            'certification_date': res_data['fecha'],
        }
