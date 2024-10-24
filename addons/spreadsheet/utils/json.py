# Part of Odoo. See LICENSE file for full copyright and licensing details.

def extend_serialized_json(json: str, key_value_pairs: list) -> str:
    """
    Add key-value pairs to a serialized JSON object string.
    value should be already serialized.
    """
    # avoid copying strings as much as possible for performance reasons
    parts = [json.removesuffix('}')]
    if json != '{}':
        parts.append(',')
    for i, (key, value) in enumerate(key_value_pairs):
        parts.extend([f'"{key}":', value])
        if i != len(key_value_pairs) - 1:
            parts.append(',')
    parts.append('}')
    return ''.join(parts)
