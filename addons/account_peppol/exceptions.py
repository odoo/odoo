from typing import Callable

from odoo import _

# Error mapping of code to message strings from Peppol IAP (peppol_proxy/exceptions.py)
# We need to wrap all the message inside lambda to make sure they will be called on demand,
# with a language context in the environment

# Standard errors (stored as `code`)
STANDARD_EXCEPTION_CODE_MESSAGES_MAP: dict[int, Callable[..., str]] = {
    101: lambda: _('Something went wrong with your request'),
    102: lambda arg: _('Proxy error, please contact Odoo (missing "%s" - please make sure that it was loaded from the configuration panel)', arg),
    103: lambda: _('The document could not be validated.'),
    104: lambda arg: _('Could not find an XSD with which to validate the document with identifier "%s".', arg),
    105: lambda: _('The XML document is not valid according to the XSD Schema.'),
    106: lambda: _('The XML document is not valid according to the schematron.'),
    107: lambda: _('The XML document could not be canonicalized.'),
    201: lambda: _('There was an issue with the Peppol Participant.'),
    202: lambda: _('This user\'s is not a Peppol User. The proxy_type associated must be "peppol". This is required to create a peppol participant.'),
    203: lambda arg: _('The Service Metadata Publisher associated to this participant is not reachable. url: %s', arg),
    204: lambda: _('The Peppol Participant service group found on his Service Metadata Provider is invalid.'),
    205: lambda: _('No valid AS4 participant endpoint were found.'),
    206: lambda: _('The Peppol Participant DNS lookup resulted in an URL address that does not belong to this server.'),
    207: lambda: _('The Peppol Participant cannot receive this document type.'),
    208: lambda: _('The Peppol Participant certificate is invalid.'),
    301: lambda: _('No UBL document was provided to the Peppol Outbound Service.'),
    302: lambda: _('The UBL document provided to the Peppol Outbound Service is malformed.'),
    303: lambda: _('The document could not be sent to the Peppol Participant.'),
    304: lambda: _('There was an issue with the Hermes Migration Token Collection Interface (MTCI).'),
    501: lambda: _('There was an error with the incoming message.'),
    502: lambda: _('This user is not registered on our Access Point.'),
    503: lambda: _('Unexpected end of MIME multipart message.'),
    504: lambda: _('Unable to verify the digest value.'),
    505: lambda: _('The encrypted data reference the Security header intended for the "ebms" SOAP actor could not be decrypted by the Security Module.'),
    506: lambda: _('The message does not comply with the AS4 policy.'),
    507: lambda: _('The incoming message could not be decompressed.'),
    701: lambda: _('There was an error with the Peppol Request'),
    702: lambda: _('Your request is still being processed.'),
    703: lambda: _('Your identification has not been approved for this action yet'),
    704: lambda: _('An internal error occurred'),
    705: lambda: _('You don\'t have enough credit'),
    706: lambda: _('The document could not be found'),
    707: lambda: _('You have reached the limit of documents you can send today. Retry later. Please contact the support if you think you need to increase that limit.'),
    708: lambda: _('You are not authorized to change the contact email.'),
}


# Errors from the ebMS standard (stored as `ebms_code`)
EBMS_EXCEPTION_CODE_MESSAGES_MAP: dict[int, Callable[..., str]] = {
    1: lambda: _('Although the message document is well formed and schema valid, some element/attribute contains a value that could not be recognized and therefore could not be used by the MSH.'),
    2: lambda: _('Although the message document is well formed and schema valid, some element/attribute value cannot be processed as expected because the related feature is not supported by the MSH.'),
    3: lambda: _('Although the message document is well formed and schema valid, some element/attribute value is inconsistent either with the content of other element/attribute, or with the processing mode of the MSH, or with the normative requirements of the ebMS specification.'),
    4: lambda: _('Other'),
    5: lambda: _('The MSH is experiencing temporary or permanent failure in trying to open a transport connection with a remote MSH.'),
    6: lambda: _('There is no message available for pulling from this MPC at this moment.'),
    7: lambda: _('The use of MIME is not consistent with the required usage in this specification.'),
    8: lambda: _('Although the message document is well formed and schema valid, the presence or absence of some element/ attribute is not consistent with the capability of the MSH, with respect to supported features.'),
    9: lambda: _('The ebMS header is either not well formed as an XML document, or does not conform to the ebMS packaging rules.'),
    10: lambda: _('The ebMS header or another header (e.g. reliability, security) expected by the MSH is not compatible with the expected content, based on the associated P-Mode.'),
    101: lambda: _('The signature in the Security header intended for the "ebms" SOAP actor, could not be validated by the Security module.'),
    102: lambda: _('The encrypted data reference the Security header intended for the "ebms" SOAP actor could not be decrypted by the Security Module.'),
    103: lambda: _('The processor determined that the message\'s security methods, parameters, scope or other security policy-level requirements or agreements were not satisfied.'),
    11: lambda: _('The MSH is unable to resolve an external payload reference (i.e. a Part that is not contained within the ebMS Message, as identified by a PartInfo/href URI).'),
    20: lambda: _('An Intermediary MSH was unable to route an ebMS message and stopped processing the message.'),
    201: lambda: _('Some reliability function as implemented by the Reliability module, is not operational, or the reliability state associated with this message sequence is not valid.'),
    202: lambda: _('Although the message was sent under Guaranteed delivery requirement, the Reliability module could not get assurance that the message was properly delivered, in spite of resending efforts.'),
    21: lambda: _('An entry in the routing function is matched that assigns the message to an MPC for pulling, but the intermediary MSH is unable to store the message with this MPC'),
    22: lambda: _('An intermediary MSH has assigned the message to an MPC for pulling and has successfully stored it. However the intermediary set a limit on the time it was prepared to wait for the message to be pulled, and that limit has been reached.'),
    23: lambda: _('An MSH has determined that the message is expired and will not attempt to forward or deliver it.'),
    30: lambda: _('The structure of a received bundle is not in accordance with the bundling rules.'),
    301: lambda: _('A Receipt has not been received  for a message that was previously sent by the MSH generating this error.'),
    302: lambda: _('A Receipt has been received  for a message that was previously sent by the MSH generating this error, but the content does not match the message content (e.g. some part has not been acknowledged, or the digest associated does not match the signature digest, for NRR).'),
    303: lambda: _('An error occurred during the decompression.'),
    31: lambda: _('A message unit in a bundle was not processed because a related message unit in the bundle caused an error.'),
    40: lambda: _('A fragment is received that relates to a group that was previously rejected.'),
    41: lambda: _('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    42: lambda: _('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    43: lambda: _('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    44: lambda: _('A fragment is received but more than one fragment message in a group of fragments specifies a value for this element.'),
    45: lambda: _('A fragment is received but more than one fragment message in a group of fragments specifies a value for a compression element.'),
    46: lambda: _('A fragment is received but a previously received fragment message had the same values for GroupId and FragmentNum'),
    47: lambda: _('The href attribute does not reference a valid MIME data part, MIME parts other than the fragment header and a data part are in the message. are added or the SOAP Body is not empty.'),
    48: lambda: _('An incoming message fragment has a a value greater than the known FragmentCount.'),
    49: lambda: _('A value is set for FragmentCount, but a previously received fragment had a greature value.'),
    50: lambda arg: _('The size of the data part in a fragment message is greater than %s', arg),
    51: lambda arg: _('More time than %s has passed since the first fragment was received but not all other fragments are received.', arg),
    52: lambda arg: _('Message properties were present in the fragment SOAP header that were not specified in %s', arg),
    53: lambda: _('The eb3:Message header copied to the fragment header does not match the eb3:Message header in the reassembled source message.'),
    54: lambda: _('Not enough disk space available to store all (expected) fragments of the group.'),
    55: lambda: _('An error occurred while decompressing the reassembled message.'),
    60: lambda: _('A responding MSH indicates that it applies the alternate MEP binding to the response message.'),
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


def get_exception_message(error_vals: dict):
    """
    :param error_vals: this dictionary must contain the following keys:
    - 'code': <str>
    - 'args': <list[str]>
    :return: the translated standard error message
    """
    peppol_code = error_vals['code']
    if peppol_code not in STANDARD_EXCEPTION_CODE_MESSAGES_MAP:
        return _('Unknown Peppol Error: %s', error_vals)

    translation_lambda = STANDARD_EXCEPTION_CODE_MESSAGES_MAP[peppol_code]
    return _get_translation_lambda_message(translation_lambda, error_vals['args'])


def get_ebms_message(error_vals: dict):
    """
    :param error_vals: this dictionary must contain the following keys:
    - 'ebms_code': <str>
    - 'args': <list[str]>
    :return: the translated EBMS error message
    """
    ebms_code = error_vals['ebms_code']
    if ebms_code not in EBMS_EXCEPTION_CODE_MESSAGES_MAP:
        return _('Unknown Peppol Error: %s', error_vals)

    translation_lambda = EBMS_EXCEPTION_CODE_MESSAGES_MAP[ebms_code]
    return _get_translation_lambda_message(translation_lambda, error_vals['args'])
