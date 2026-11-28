import re


def street_split(street):
    """Split a street into its name and number, the number being either at the end or at the beginning."""
    if not street:
        return {'street_name': '', 'street_number': ''}
    street = street.strip()

    # number at the end
    match = re.match(r'^(.+?)\s+(\d+[-/]?\d*\s*\w*)$', street)
    if match:
        return {
            'street_name': match.group(1).strip(),
            'street_number': match.group(2).strip(),
        }

    # number at the beginning
    match = re.match(r'^(\d+[-/]?\d*\s*\w?)\s+(.+)$', street)
    if match:
        return {
            'street_name': match.group(2).strip(),
            'street_number': match.group(1).strip(),
        }
    return {'street_name': street, 'street_number': ''}


def get_greek_vat_number(vat):
    """myDATA expects Greek VAT numbers without their country prefix."""
    vat = (vat or '').strip()
    if vat[:2].upper() in ('EL', 'GR'):
        return vat[2:]
    return vat
