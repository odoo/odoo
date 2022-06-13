from itertools import zip_longest


def calc_check_digits(number: str) -> str:
    """Calculate the extra digits that should be appended to the number to make it a valid number.
    Source: python-stdnum iso7064.mod_97_10.calc_check_digits
    """
    number_base10 = ''.join(str(int(x, 36)) for x in number)
    checksum = int(number_base10) % 97
    return '%02d' % ((98 - 100 * checksum) % 97)


def format_rf_reference(number: str) -> str:
    """Format a string into a Structured Creditor Reference.

    The Creditor Reference is an international standard (ISO 11649).
    Example: `123456789` -> `RF18 1234 5678 9`
    """
    check_digits = calc_check_digits('{}RF'.format(number))
    return 'RF{} {}'.format(
        check_digits,
        " ".join("".join(x) for x in zip_longest(*[iter(str(number))]*4, fillvalue=""))
    )
