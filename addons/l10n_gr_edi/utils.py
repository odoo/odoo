import re


def street_split(street):
    if not street:
        return {'street_name': '', 'street_number': ''}
    street = street.strip()

    # number in the beginning
    match = re.match(r'^(.+?)\s+(\d+[-/]?\d*\s*\w*)$', street)
    if match:
        return {
            'street_name': match.group(1).strip(),
            'street_number': match.group(2).strip(),
        }

    # number at the end
    match = re.match(r'^(\d+[-/]?\d*\s*\w?)\s+(.+)$', street)
    if match:
        return {
            'street_name': match.group(2).strip(),
            'street_number': match.group(1).strip(),
        }
    return {'street_name': street, 'street_number': ''}


def get_pre_error_string(pre_error):
    error_messages = (error_val['message'] for error_val in pre_error.values())
    return '\n'.join(error_messages)
