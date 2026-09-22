"""Cache identity for the `/doc` documents.

Two things are named here, and they have to agree: the ETag a client caches
under, and the attachment name the server stores the index under. Both are
derived from the same *generation* -- the state of the database that the
document's content depends on -- which is what lets the garbage collector
recognise, with a domain and no Python filtering, every index that can no
longer be served.
"""

import hashlib

INDEX_NAME_PREFIX = "odoo-doc-index-"

#: The cache groups whose sequence gates what a user may see. `stable` is what
#: an ``ir.model.access`` / ``ir.model.fields`` write moves and `groups` what a
#: ``res.groups`` write moves; between them they cover every input to the
#: `has_access` / `_has_field_access` filtering the documents apply.
#:
#: `default` is deliberately absent. It moves on ordinary ORM cache
#: invalidation, which would rebuild a multi-megabyte index for writes that
#: cannot change a single line of it.
ACCESS_CACHE_SEQUENCES = ("stable", "groups")


def doc_cache_generation(env):
    """A short digest of every database state the `/doc` documents depend on.

    :param env: any environment
    :return: 12 hex characters, changing whenever a document could
    :rtype: str
    """
    registry_sequence, cache_sequences = env.registry.get_sequences(env.cr)
    material = (
        registry_sequence,
        *(cache_sequences[name] for name in ACCESS_CACHE_SEQUENCES),
    )
    return hashlib.blake2b(repr(material).encode(), digest_size=6).hexdigest()


def index_attachment_name(generation, unique):
    """The attachment name an index is cached under.

    :param str generation: from :func:`doc_cache_generation`
    :param str unique: the per-user, per-language ETag
    :rtype: str
    """
    return f"{INDEX_NAME_PREFIX}{generation}-{unique}.json"


def stale_index_domain(generation):
    """Match every cached index that is not of the current generation.

    :param str generation: from :func:`doc_cache_generation`
    :return: an ``ir.attachment`` domain
    :rtype: list
    """
    return [
        ("name", "=like", f"{INDEX_NAME_PREFIX}%"),
        ("name", "not like", f"{INDEX_NAME_PREFIX}{generation}-"),
    ]
