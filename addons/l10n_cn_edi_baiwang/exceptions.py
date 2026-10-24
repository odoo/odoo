# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)

BAIWANG_ERROR_CODE_MESSAGES = {
    '70169': _lt('Required parameter is missing.'),
    '70170': _lt('A request parameter is invalid.'),
    '101': _lt('Authentication failed. Please verify your Baiwang credentials.'),
    '103': _lt('Authorization has expired. Please re-authorize.'),
    '907': _lt('Invoice verification service is not enabled.'),
    '910': _lt('Input invoice service is not enabled.'),
    '14': _lt('Daily verification quota is exhausted. Please retry later.'),
    '402': _lt('Daily verification limit for this invoice has been reached.'),
    '99': _lt('Previous verification is still processing. Retry in a few minutes.'),
    '410': _lt('Tax bureau verification service is temporarily unavailable. Retry later.'),
    '411': _lt('Verification failed temporarily. Retry later.'),
    '416': _lt('Verification system is busy. Retry later.'),
    '606': _lt('Invoice is still processing. Retry later.'),
}

RETRYABLE_CODES = {'99', '410', '411', '416', '606'}


def get_baiwang_error_message(env, _error_reference, error_data):
    error_data = error_data if isinstance(error_data, dict) else {}
    code = str(error_data.get('code') or '')
    provider_message = error_data.get('message') or env._('Unexpected Baiwang error.')
    if error_data.get('subCode'):
        provider_message = f"{provider_message} ({error_data.get('subCode')}: {error_data.get('subMessage') or ''})"
    mapped = BAIWANG_ERROR_CODE_MESSAGES.get(code)
    if mapped:
        return env._(
            '%(mapped_message)s (Baiwang [%(code)s]: %(provider_message)s)',
            mapped_message=mapped,
            code=code,
            provider_message=provider_message,
        )
    if code:
        return env._(
            'Baiwang error [%(code)s]: %(provider_message)s',
            code=code,
            provider_message=provider_message,
        )
    return provider_message
