import json
import re
from importlib import import_module

from odoo.tools import file_open

FILE_NAME = 'peppol_code_lists_participant_identifier_scheme.json'

ADDITIONAL_CHECK = [
    {'eas': '0009', 'module': 'stdnum.fr.siret'},
    {'eas': '0208', 'module': 'stdnum.be.vat'},
    {'eas': '9925', 'module': 'stdnum.be.vat'},
    {'eas': '9926', 'module': 'stdnum.bg.vat'},
    {'eas': '9927', 'module': 'stdnum.ch.vat'},
    {'eas': '9928', 'module': 'stdnum.cy.vat'},
    {'eas': '9930', 'module': 'stdnum.de.vat'},
    {'eas': '9932', 'module': 'stdnum.gb.vat'},
    {'eas': '9933', 'module': 'stdnum.gr.vat'},
    {'eas': '9935', 'module': 'stdnum.ie.vat'},
    {'eas': '9938', 'module': 'stdnum.lu.tva'},
    {'eas': '9940', 'module': 'stdnum.mc.tva'},
    {'eas': '9957', 'module': 'stdnum.fr.tva'},
]


def validate_eas_endpoint_format(eas: str, endpoint: str) -> dict:
    """
    This method checks if a given endpoint for a given eas is valid.
    :param eas: The eas used to check the endpoint
    :param endpoint: The endpoint to check
    :return: A dict containing 2 fields {'valid': bool, 'examples': str/False}
    """
    regex = _get_validation_regex_for_eas(eas)
    if re.match(regex[1], endpoint):
        if _perform_additional_check(eas, endpoint):
            return {'valid': True, 'examples': False}
    return {'valid': False, 'examples': regex[2]}


def _get_validation_regex_for_eas(eas):
    """
    This method returns a tuple with the validation regex and an example (if found)
    for the eas given as a parameter
    :param eas: The eas used to search the regex
    :return: A tuple with (eas, regex, examples)
    """
    data = _read_eas_data(eas)
    res = (eas,)
    if data and 'validation-rules' in data and 'RegEx' in data['validation-rules']:
        for line in data['validation-rules'].split('\n'):
            if 'RegEx' in line.split()[0]:
                res += ('^' + line.split()[1].strip() + '$',)
                break
        res += (data['examples'].replace('\n', ' or '),) if 'examples' in data else (False,)
    else:
        # Default RegEx if not found in the file or if it's not active
        res += ('^[a-zA-Z\\d\\-._~]{1,50}$', False)
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


def _perform_additional_check(eas, endpoint):
    """
    This method perform an additional check on the endpoint format.
    :param eas: The eas code we try to check the data for.
    :param endpoint: The value to check.
    :return: A boolean, False if the endpoint doesn't fit the format, otherwise True
    """
    check_data = _get_check_data(eas)
    if not check_data:
        return True

    if check_data.get('module') and check_data.get('function'):
        # A function located in another module
        return _get_func(check_data['module'], check_data['function'])(endpoint)
    elif check_data.get('function'):
        # A local function, no need to import the module
        return globals()[check_data['function']](endpoint)
    else:
        return True


def _get_check_data(eas):
    """
    Reads data from the ADDITIONAL_CHECK dictionary for the given eas. This data will be used later to perform a check
    based on a field (e.g. 9925 in BE, we'll check if the endpoint value is a valid vat)
    :param eas: The eas code used to read the data.
    :returns: A dictionary containing the data to check the eas or False if no additional check is needed.
    * eas:      str: The eas code.
    * module:   str: The module in which the validation function can be found.
    * function: str: The function to validate the format.
    """
    for check in ADDITIONAL_CHECK:
        if check['eas'] == eas:
            return check
    return False


def _get_func(module_str, function_str):
    """
    Returns a reference to the function 'function_str' in the module 'module_str',
    or a lambda returning True if an error is raised.
    :param module_str: The module where the function is located.
    :param function_str: The function name.
    :return: A reference to the function.
    """
    # Here we import the modules 1 by 1, e.g. if module_str = 'stdnum.fr.siret' we first import 'stdnum' by calling __import__,
    # then, we will loop to get all modules until the last one (siret in this case) with 'getattr()'.
    # And finally we get the function reference by calling 'getattr(<final_module>, function_str)'
    try:
        module = import_module(module_str)
        return module.is_valid
    except (AttributeError, ModuleNotFoundError):
        return lambda l: True
