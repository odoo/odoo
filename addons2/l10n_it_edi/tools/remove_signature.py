# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import warnings

_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto as ssl_crypto
    import OpenSSL._util as ssl_util
except ImportError:
    ssl_crypto = None
    _logger.warning("Cannot import library 'OpenSSL' for PKCS#7 envelope extraction.")


def remove_signature(content):
    """ Remove the PKCS#7 envelope from given content, making a '.xml.p7m' file content readable as it was '.xml'.
        As OpenSSL may not be installed, in that case a warning is issued and None is returned. """

    # Prevent using the library if it had import errors
    if not ssl_crypto:
        _logger.warning("Error reading the content, check if the OpenSSL library is installed for for PKCS#7 envelope extraction.")
        return None

    # Load some tools from the library
    null = ssl_util.ffi.NULL
    verify = ssl_util.lib.PKCS7_verify

    # By default ignore the validity of the certificates, just validate the structure
    flags = ssl_util.lib.PKCS7_NOVERIFY | ssl_util.lib.PKCS7_NOSIGS

    # Read the signed data fron the content
    out_buffer = ssl_crypto._new_mem_buf()

    # This method is deprecated, but there are actually no alternatives
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        try:
            loaded_data = ssl_crypto.load_pkcs7_data(ssl_crypto.FILETYPE_ASN1, content)
        except ssl_crypto.Error:
            _logger.debug("PKCS#7 signature missing or invalid. Content will be tentatively used as plain text.")
            return content

    # Verify the signature
    if verify(loaded_data._pkcs7, null, null, null, out_buffer, flags) != 1:
        ssl_crypto._raise_current_error()

    # Get the content as a byte-string
    decoded_content = ssl_crypto._bio_to_string(out_buffer)
    return decoded_content
