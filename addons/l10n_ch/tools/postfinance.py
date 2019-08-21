# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo.tools.misc import mod10r

CLEARING = "09000"

_re_postal = re.compile('^[0-9]{2}-[0-9]{1,6}-[0-9]$')


def is_postal_num(account_ref):
    """ Returns True if the string account_ref is a valid postal account number,
    i.e. it only contains ciphers and is last cipher is the result of a recursive
    modulo 10 operation ran over the rest of it. Shorten form with - is also accepted.
    """
    if _re_postal.match(account_ref or ''):
        ref_subparts = account_ref.split('-')
        account_ref = ref_subparts[0] + ref_subparts[1].rjust(6, '0') + ref_subparts[2]

    if re.match('\d+$', account_ref or ''):
        account_ref_without_check = account_ref[:-1]
        return mod10r(account_ref_without_check) == account_ref
    return False


def is_postfinance_iban(iban):
    """Postfinance IBAN have format
    CHXX 0900 0XXX XXXX XXXX K
    Where 09000 is the clearing number
    """
    return (iban.startswith('CH')
            and iban[4:9] == CLEARING)


def _pretty_postal_num(number):
    """format a postal account number or an ISR subscription number
    as per specifications with '-' separators.
    eg. 010000628 -> 01-162-8
    """
    if re.match('^[0-9]{2}-[0-9]{1,6}-[0-9]$', number or ''):
        return number
    currency_code = number[:2]
    middle_part = number[2:-1]
    trailing_cipher = number[-1]
    middle_part = re.sub('^0*', '', middle_part)
    return currency_code + '-' + middle_part + '-' + trailing_cipher

def iban_to_postal(iban):
    """Reads a swiss postal account number from a an IBAN and returns it as
    a string. Returns None if no valid postal account number was found, or
    the given iban was not from Swiss Postfinance.

    CH09 0900 0000 1000 8060 7 -> 10-8060-7
    """
    # We can deduce postal account number only if
    # the financial institution is PostFinance
    if is_postfinance_iban(iban):
        #the IBAN corresponds to a swiss account
        return _pretty_postal_num(iban[-9:])
    return None
