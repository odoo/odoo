from typing import Callable

from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)

# Error mapping of code to message strings from Peppol IAP (peppol_proxy/exceptions.py)
# We need to wrap all the message inside lambda to make sure they will be called on demand,
# with a language context in the environment

# Standard errors (stored as `code`)
STANDARD_EXCEPTION_CODE_MESSAGES_MAP: dict[int, Callable[..., str]] = {
    101: lambda: _lt('Something went wrong with your request'),
    102: lambda arg: _lt('Proxy error, please contact Odoo (missing "%s" - please make sure that it was loaded from the configuration panel)', arg),
    103: lambda: _lt('The document could not be validated.'),
    104: lambda arg: _lt('Could not find an XSD with which to validate the document with identifier "%s".', arg),
    105: lambda: _lt('The XML document is not valid according to the XSD Schema.'),
    106: lambda: _lt('The XML document is not valid according to the schematron.'),
    107: lambda: _lt('The XML document could not be canonicalized.'),
    201: lambda: _lt('There was an issue with the Peppol Participant.'),
    202: lambda: _lt('This user\'s is not a Peppol User. The proxy_type associated must be "peppol". This is required to create a peppol participant.'),
    203: lambda arg: _lt('The Service Metadata Publisher associated to this participant is not reachable. url: %s', arg),
    204: lambda: _lt('The Peppol Participant service group found on his Service Metadata Provider is invalid.'),
    205: lambda: _lt('No valid AS4 participant endpoint were found.'),
    206: lambda: _lt('The Peppol Participant DNS lookup resulted in an URL address that does not belong to this server.'),
    207: lambda: _lt('The Peppol Participant cannot receive this document type.'),
    208: lambda: _lt('The Peppol Participant certificate is invalid.'),
    301: lambda: _lt('No UBL document was provided to the Peppol Outbound Service.'),
    302: lambda: _lt('The UBL document provided to the Peppol Outbound Service is malformed.'),
    303: lambda: _lt('The document could not be sent to the Peppol Participant.'),
    304: lambda: _lt('There was an issue with the Hermes Migration Token Collection Interface (MTCI).'),
    501: lambda: _lt('There was an error with the incoming message.'),
    502: lambda: _lt('This user is not registered on our Access Point.'),
    503: lambda: _lt('Unexpected end of MIME multipart message.'),
    504: lambda: _lt('Unable to verify the digest value.'),
    505: lambda: _lt('The encrypted data reference the Security header intended for the "ebms" SOAP actor could not be decrypted by the Security Module.'),
    506: lambda: _lt('The message does not comply with the AS4 policy.'),
    507: lambda: _lt('The incoming message could not be decompressed.'),
    701: lambda: _lt('There was an error with the Peppol Request'),
    702: lambda: _lt('Your request is still being processed.'),
    703: lambda: _lt('Your identification has not been approved for this action yet'),
    704: lambda: _lt('An internal error occurred'),
    705: lambda: _lt('You don\'t have enough credit'),
    706: lambda: _lt('The document could not be found'),
    707: lambda: _lt('You have reached the limit of documents you can send today. Retry later. Please contact the support if you think you need to increase that limit.'),
    708: lambda: _lt('You are not authorized to change the contact email.'),
}


# Errors from the ebMS standard (stored as `ebms_code`)
EBMS_EXCEPTION_CODE_MESSAGES_MAP: dict[int, Callable[..., str]] = {
    1: lambda: _lt('Although the message document is well formed and schema valid, some element/attribute contains a value that could not be recognized and therefore could not be used by the MSH.'),
    2: lambda: _lt('Although the message document is well formed and schema valid, some element/attribute value cannot be processed as expected because the related feature is not supported by the MSH.'),
    3: lambda: _lt('Although the message document is well formed and schema valid, some element/attribute value is inconsistent either with the content of other element/attribute, or with the processing mode of the MSH, or with the normative requirements of the ebMS specification.'),
    4: lambda: _lt('Other'),
    5: lambda: _lt('The MSH is experiencing temporary or permanent failure in trying to open a transport connection with a remote MSH.'),
    6: lambda: _lt('There is no message available for pulling from this MPC at this moment.'),
    7: lambda: _lt('The use of MIME is not consistent with the required usage in this specification.'),
    8: lambda: _lt('Although the message document is well formed and schema valid, the presence or absence of some element/ attribute is not consistent with the capability of the MSH, with respect to supported features.'),
    9: lambda: _lt('The ebMS header is either not well formed as an XML document, or does not conform to the ebMS packaging rules.'),
    10: lambda: _lt('The ebMS header or another header (e.g. reliability, security) expected by the MSH is not compatible with the expected content, based on the associated P-Mode.'),
    101: lambda: _lt('The signature in the Security header intended for the "ebms" SOAP actor, could not be validated by the Security module.'),
    102: lambda: _lt('The encrypted data reference the Security header intended for the "ebms" SOAP actor could not be decrypted by the Security Module.'),
    103: lambda: _lt('The processor determined that the message\'s security methods, parameters, scope or other security policy-level requirements or agreements were not satisfied.'),
    11: lambda: _lt('The MSH is unable to resolve an external payload reference (i.e. a Part that is not contained within the ebMS Message, as identified by a PartInfo/href URI).'),
    20: lambda: _lt('An Intermediary MSH was unable to route an ebMS message and stopped processing the message.'),
    201: lambda: _lt('Some reliability function as implemented by the Reliability module, is not operational, or the reliability state associated with this message sequence is not valid.'),
    202: lambda: _lt('Although the message was sent under Guaranteed delivery requirement, the Reliability module could not get assurance that the message was properly delivered, in spite of resending efforts.'),
    21: lambda: _lt('An entry in the routing function is matched that assigns the message to an MPC for pulling, but the intermediary MSH is unable to store the message with this MPC'),
    22: lambda: _lt('An intermediary MSH has assigned the message to an MPC for pulling and has successfully stored it. However the intermediary set a limit on the time it was prepared to wait for the message to be pulled, and that limit has been reached.'),
    23: lambda: _lt('An MSH has determined that the message is expired and will not attempt to forward or deliver it.'),
    30: lambda: _lt('The structure of a received bundle is not in accordance with the bundling rules.'),
    301: lambda: _lt('A Receipt has not been received  for a message that was previously sent by the MSH generating this error.'),
    302: lambda: _lt('A Receipt has been received  for a message that was previously sent by the MSH generating this error, but the content does not match the message content (e.g. some part has not been acknowledged, or the digest associated does not match the signature digest, for NRR).'),
    303: lambda: _lt('An error occurred during the decompression.'),
    31: lambda: _lt('A message unit in a bundle was not processed because a related message unit in the bundle caused an error.'),
    40: lambda: _lt('A fragment is received that relates to a group that was previously rejected.'),
    41: lambda: _lt('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    42: lambda: _lt('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    43: lambda: _lt('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    44: lambda: _lt('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    45: lambda: _lt('A fragment is received but more than one fragment message in a group of fragments specifies a value for a compression element.'),
    46: lambda: _lt('A fragment is received but a previously received fragment message had the same values for GroupId and FragmentNum'),
    47: lambda: _lt('The href attribute does not reference a valid MIME data part, MIME parts other than the fragment header and a data part are in the message. are added or the SOAP Body is not empty.'),
    48: lambda: _lt('An incoming message fragment has a a value greater than the known FragmentCount.'),
    49: lambda: _lt('A value is set for FragmentCount, but a previously received fragment had a greature value.'),
    50: lambda arg: _lt('The size of the data part in a fragment message is greater than %s', arg),
    51: lambda arg: _lt('More time than %s has passed since the first fragment was received but not all other fragments are received.', arg),
    52: lambda arg: _lt('Message properties were present in the fragment SOAP header that were not specified in %s', arg),
    53: lambda: _lt('The eb3:Message header copied to the fragment header does not match the eb3:Message header in the reassembled source message.'),
    54: lambda: _lt('Not enough disk space available to store all (expected) fragments of the group.'),
    55: lambda: _lt('An error occurred while decompressing the reassembled message.'),
    60: lambda: _lt('A responding MSH indicates that it applies the alternate MEP binding to the response message.'),
}


def _get_translation_lambda_message(translation_lambda: Callable[..., str], args: list[str]):
    translation_lambda_arg_count: int = translation_lambda.__code__.co_argcount

    if translation_lambda_arg_count == 0:
        return translation_lambda()
    elif translation_lambda_arg_count == len(args):
        return translation_lambda(*args)
    else:
        # The translation lambda require a number of arguments that doesn't match
        # the received number of args from the `args` list.
        # To prevent TypeError of mismatching expected positional argument,
        # we'll create a dummy args and call the translation lambda with it.
        dummy_args = ['<unknown>'] * translation_lambda_arg_count
        return translation_lambda(*dummy_args)


def get_peppol_error_message(env, error_vals: dict):
    """
    Helper to process the error dictionary returned from the IAP response.
    It will only get the code (or EBMS code) and map it to the correct translated message.
    :param dict error_vals: the dictionary of encoded error json generated from the `_json` method in `peppol_proxy`
    :return: the translated error message
    :rtype: str
    """
    # handles errors raised directly from jsonrpc routes instead of being caught and converted
    if error_vals.get('data', {}).get('context'):
        error_vals = error_vals['data']['context']
    if (ebms_code := error_vals.get('ebms_code')) and ebms_code != 4:
        # Error with ebMS code is originally from PeppolInboundError
        # In most case, ebMS message will be better and more specific, except for when the code is 4 (general "Other" message)
        error_message = get_ebms_message(env, error_vals)
    else:
        error_message = get_exception_message(env, error_vals)

    return env._(
        "Peppol Error [code=%(error_code)s]: %(error_subject)s\n%(error_message)s",
        error_code=error_vals['code'],
        error_subject=error_vals.get('subject', ''),
        error_message=error_message,
    )


def get_exception_message(env, error_vals: dict):
    """
    :param error_vals: this dictionary must contain the following keys:
    - 'code': <str>
    - 'args': <list[str]>
    :return: the translated standard error message
    """
    peppol_code = error_vals['code']
    if peppol_code not in STANDARD_EXCEPTION_CODE_MESSAGES_MAP:
        return env._('Unknown Peppol Error: %s', error_vals)

    translation_lambda = STANDARD_EXCEPTION_CODE_MESSAGES_MAP[peppol_code]
    return _get_translation_lambda_message(translation_lambda, error_vals.get('args', []))


def get_ebms_message(env, error_vals: dict):
    """
    :param error_vals: this dictionary must contain the following keys:
    - 'ebms_code': <str>
    - 'args': <list[str]>
    :return: the translated EBMS error message
    """
    ebms_code = error_vals['ebms_code']
    if ebms_code not in EBMS_EXCEPTION_CODE_MESSAGES_MAP:
        return env._('Unknown Peppol Error: %s', error_vals)

    translation_lambda = EBMS_EXCEPTION_CODE_MESSAGES_MAP[ebms_code]
    return _get_translation_lambda_message(translation_lambda, error_vals['args'])
