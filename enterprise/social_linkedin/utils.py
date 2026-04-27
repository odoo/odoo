def urn_to_id(obj_urn):
    """Convert a URN to an id.

    E.G.
    >>> urn:li:image:1337 -> 1337
    """
    if not obj_urn:
        return ''
    if obj_urn.startswith('urn:li:comment') and ',' in obj_urn:
        # urn:li:comment:(urn:li:activity:1234,5678) -> 5678
        return obj_urn.split(',')[-1].rstrip(')')
    return obj_urn.split(':')[-1]


def id_to_urn(obj_id, name):
    """Convert an id to a URN or change the name of a URN.

    E.G.
    >>> 1337 -> urn:li:image:1337
    >>> urn:li:digitalmediaAsset:1337 -> urn:li:image:1337
    """
    return f'urn:{name}:{urn_to_id(obj_id)}' if obj_id else ''
