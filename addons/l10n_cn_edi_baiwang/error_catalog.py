# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _

BAIWANG_ERROR_MAP = {
    '70169': _('Required parameter is missing.'),
    '70170': _('A request parameter is invalid.'),
    '101': _('Authentication failed. Please verify your Baiwang credentials.'),
    '103': _('Authorization has expired. Please re-authorize.'),
    '907': _('Invoice verification service is not enabled.'),
    '910': _('Input invoice service is not enabled.'),
    '14': _('Daily verification quota is exhausted. Please retry later.'),
    '402': _('Daily verification limit for this invoice has been reached.'),
    '99': _('Previous verification is still processing. Retry in a few minutes.'),
    '410': _('Tax bureau verification service is temporarily unavailable. Retry later.'),
    '411': _('Verification failed temporarily. Retry later.'),
    '416': _('Verification system is busy. Retry later.'),
    '606': _('Invoice is still processing. Retry later.'),
}

RETRYABLE_CODES = {'99', '410', '411', '416', '606'}


def map_baiwang_error(env, reference, data):
    code = str((data or {}).get('code') or '')
    provider_message = (data or {}).get('message') or env._('Unexpected Baiwang error.')
    mapped = BAIWANG_ERROR_MAP.get(code)
    if mapped:
        return env._('%s (Baiwang [%s]: %s)') % (mapped, code, provider_message)
    if code:
        return env._('Baiwang error [%s]: %s') % (code, provider_message)
    return provider_message
