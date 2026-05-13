import hashlib
import json


def serialize_eta_document(payload):
    if not isinstance(payload, dict):
        return json.dumps(str(payload), ensure_ascii=False)
    canonical_str = []
    for key, value in payload.items():
        if isinstance(value, list):
            canonical_str.append(json.dumps(key, ensure_ascii=False).upper())
            for elem in value:
                canonical_str.append(json.dumps(key, ensure_ascii=False).upper())
                canonical_str.append(serialize_eta_document(elem))
        else:
            canonical_str.append(json.dumps(key, ensure_ascii=False).upper())
            canonical_str.append(serialize_eta_document(value))
    return ''.join(canonical_str)


def compute_eta_uuid(payload):
    return hashlib.sha256(serialize_eta_document(payload).encode()).hexdigest()
