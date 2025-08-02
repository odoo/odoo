IDS_SEPARATOR = ':'

def combine_ids(ms_id, ms_uid):
    if not ms_id:
        return False
    return ms_id + IDS_SEPARATOR + (ms_uid if ms_uid else '')

def split_ids(value):
    ids = value.split(IDS_SEPARATOR)
    return tuple(ids) if len(ids) > 1 and ids[1] else (ids[0], False)
