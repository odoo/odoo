# Part of Odoo. See LICENSE file for full copyright and licensing details.

BAIWANG_ERROR_CODE_MESSAGES = {
    '70169': 'Required parameter is missing.',
    '70170': 'A request parameter is invalid.',
    '101': 'Authentication failed. Please verify your Baiwang credentials.',
    '103': 'Authorization has expired. Please re-authorize.',
    '907': 'Invoice verification service is not enabled.',
    '910': 'Input invoice service is not enabled.',
    '14': 'Daily verification quota is exhausted. Please retry later.',
    '402': 'Daily verification limit for this invoice has been reached.',
    '99': 'Previous verification is still processing. Retry in a few minutes.',
    '410': 'Tax bureau verification service is temporarily unavailable. Retry later.',
    '411': 'Verification failed temporarily. Retry later.',
    '416': 'Verification system is busy. Retry later.',
    '606': 'Invoice is still processing. Retry later.',
}

RETRYABLE_CODES = {'99', '410', '411', '416', '606'}


def get_baiwang_error_message(env, _error_reference, error_data):
    code = str((error_data or {}).get('code') or '')
    provider_message = (error_data or {}).get('message') or env._('Unexpected Baiwang error.')
    mapped = BAIWANG_ERROR_CODE_MESSAGES.get(code)
    if mapped:
        return env._('%s (Baiwang [%s]: %s)') % (env._(mapped), code, provider_message)
    if code:
        return env._('Baiwang error [%s]: %s') % (code, provider_message)
    return provider_message
