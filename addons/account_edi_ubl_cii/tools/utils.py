import json
import re

from odoo.tools import file_open

FILE_NAME = 'peppol_code_lists_participant_identifier_scheme.json'

DEFAULT_REGEX = '^[a-zA-Z\\d\\-._~]{1,50}$'


def validate_eas_endpoint_format(env, eas: str, endpoint: str) -> dict:
    """
    This method checks if a given endpoint for a given eas is valid.
    :param env: The environment, will be used to access model method
    :param eas: The eas used to check the endpoint
    :param endpoint: The endpoint to check
    :return: A dict containing 2 fields {'valid': bool, 'examples': str/False}
    """
    regex = _get_validation_regex_for_eas(eas)
    if re.match(regex['regex'], endpoint):
        if not _need_vat_check(regex['schemeid'], eas):
            return {'valid': True, 'examples': False}
        if _perform_vat_check(env, regex['schemeid'].split(':')[0], endpoint):
            return {'valid': True, 'examples': False}
    return {'valid': False, 'examples': regex['examples']}


def _get_validation_regex_for_eas(eas):
    """
    This method returns a dict with the scheme id, the validation regex and an example (if found)
    for the eas given as a parameter
    :param eas: The eas used to search the regex
    :return: A dict with {'schemeid': schemeid, 'regex': regex, 'examples': examples}
    """
    data = _read_eas_data(eas)
    res = {
        'schemeid': data['schemeid'] if data and 'schemeid' in data else '',
        'regex': DEFAULT_REGEX,
        'examples': False
    }
    if data and 'validation-rules' in data and 'RegEx' in data['validation-rules']:
        for line in data['validation-rules'].split('\n'):
            if 'RegEx' in line.split()[0]:
                res['regex'] = '^' + line.split()[1].strip() + '$'
                break
        if 'examples' in data:
            res['examples'] = data['examples'].replace('\n', ' or ')
    elif eas == '9925':
        # for now, peppol doesn't provide any regex for the 9925 (BE) eas, and the vat check that will be done after
        # is only to check if the endpoint is on the belgian vat format. This means that either BE0123456789 and 0123456789
        # will success this additional check, but we only want to accept an endpoint with format (BE)[01][0-9]{9}
        res['regex'] = '^(BE)[01][0-9]{9}$'
        res['examples'] = 'BE0976736847'

    return res


def _read_eas_data(eas):
    """
    This method returns the data found in the file 'peppol_code_lists_participant_identifier_scheme.json' for the given
    parameter eas. This data will be later used to apply a RegEx on the value of the endpoint.
    :param eas: The eas code we read the data for.
    :return: A dict containing data for the eas code or False if not found.
    """
    with (file_open(f'account_edi_ubl_cii/data/{FILE_NAME}', 'rb', filter_ext=('.json')) as file):
        content = json.load(file)
        for data in content['values']:
            if data['iso6523'] == eas:
                return data if data['state'] == 'active' else False
    return False


def _need_vat_check(scheme_id, eas):
    """
    This method determines if a vat check is needed based on the schemeid and the eas
    :param scheme_id: The scheme_id from the json file
    :param eas: The eas code
    :return: Bool True if a vat check is needed, False otherwise
    """
    try:
        return scheme_id.split(':')[1].upper() == 'VAT' or eas == '0208'
    except IndexError:
        return False


def _perform_vat_check(env, country_code, endpoint):
    """
    This method perform a vat number check on the endpoint format.
    :param env: The environment
    :param country_code: The country we try to check the data for.
    :param endpoint: The value to check.
    :return: A boolean, False if the endpoint doesn't match the format, otherwise True
    """
    return env['res.partner']._check_vat_number(country_code, endpoint)
