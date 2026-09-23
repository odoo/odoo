"""What the registry exposes over RPC, and what documents it.

The parsing engine lives in :mod:`odoo.libs.docstring`, which knows nothing
about Odoo. This module is the coupled half: which methods `/json/2` will
actually accept, which class in the MRO to credit for one, and which docstring
in that MRO describes it.
"""

import logging

from odoo.exceptions import AccessError
from odoo.libs.docstring import parse_signature, render_docstring
from odoo.service.model import get_public_method

logger = logging.getLogger(__name__)

#: Annotations naming a recordset. `/json/2` serialises one as its ids, so the
#: documented return type is what the caller receives, not what Python returns.
RPC_RECORDSET_ANNOTATIONS = frozenset(
    {
        "Self",
        "typing.Self",
        "BaseModel",
        "Model",
        "models.BaseModel",
        "models.Model",
    }
)


def normalize_rpc_return(annotation):
    """Rewrite a recordset return annotation into what RPC really sends."""
    return "list[int]" if annotation in RPC_RECORDSET_ANNOTATIONS else annotation


def is_public_method(model, name):
    """Whether ``name`` is callable on ``model`` over `/json/2`.

    Mirrors the dispatcher exactly -- same gate, same exceptions -- so the
    documentation cannot advertise a method the server would refuse. Deprecated
    methods are still callable but deliberately undocumented.

    :param model: a recordset
    :param str name: candidate method name
    :return: True when the method is public, callable and not deprecated
    :rtype: bool
    """
    try:
        method = get_public_method(model, name)
    except AttributeError, AccessError:
        return False
    return not hasattr(method, "__deprecated__")


def public_method_names(model):
    """Every `/json/2`-callable method name of ``model``.

    :param model: a recordset
    :return: the method names, in ``dir()`` order
    :rtype: list[str]
    """
    return [name for name in dir(model) if is_public_method(model, name)]


def _definers(model_cls, method_name):
    """The classes of ``model_cls``'s MRO that define ``method_name``.

    Most derived first, so ``[0]`` is the implementation that runs and ``[-1]``
    is the one that introduced the name.
    """
    return [cls for cls in model_cls.__mro__ if method_name in cls.__dict__]


def _describing_docstring(definers, method_name):
    """The most derived docstring in an override chain.

    An override that documents nothing must not erase the documentation of what
    it replaced: `res.company.write` overrides `WriteMixin.write`, and on this
    fork it is the *base* mixin that carries no prose. Walking derived to basal
    and taking the first docstring found is what makes both cases work.
    """
    for cls in definers:
        if doc := getattr(cls, method_name).__doc__:
            return doc
    return None


def reflect_callable(method, docstring=None):
    """Reflect a callable the way `/doc` publishes it.

    :param method: the implementation to describe
    :param str docstring: documentation to use instead of the callable's own
    :return: the parsed signature, with the ``@api`` flags filled in
    :rtype: odoo.libs.docstring.Signature
    """
    signature = parse_signature(
        method, docstring=docstring, normalize_return=normalize_rpc_return
    )
    signature.api = _api_flags(method)
    return signature


def describe_method(model, method_name):
    """Reflect one method into the JSON structure `/doc` publishes.

    :param model: a recordset
    :param str method_name: a name for which :func:`is_public_method` is true
    :return: the signature, parameters, docstring and provenance of the method
    :rtype: dict
    """
    model_cls = type(model)
    definers = _definers(model_cls, method_name)
    # Defensive: a name reachable by getattr but present in no __dict__ of the
    # MRO (a descriptor on the metaclass, say) still deserves a description.
    introducing = definers[-1] if definers else model_cls
    implementation = getattr(introducing, method_name)

    try:
        described = reflect_callable(
            implementation,
            docstring=_describing_docstring(definers, method_name),
        ).as_dict()
    except Exception as exc:
        # One unreflectable method must not take the whole model's page with
        # it. This is a guard, not a workaround for a known defect: the PEP 649
        # NameError class that used to land here is fixed at the source, in
        # parse_signature's annotation_format.
        logger.warning(
            "rpc/doc: could not reflect %s.%s (%s): %s",
            model._name,
            method_name,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        described = {
            "signature": "(...)",
            "parameters": {},
            "doc": f"Signature could not be introspected ({type(exc).__name__}: {exc}).",
        }

    return described | {
        # Pure-Python mixins sit in the MRO without being Odoo models, so they
        # carry neither _name nor _module. They are the framework itself.
        "model": getattr(introducing, "_name", None) or "core",
        "module": getattr(introducing, "_module", None) or "core",
    }


def _api_flags(method):
    """The `@api` decorators a caller needs to know about."""
    api = []
    if getattr(method, "_api_model", False):
        api.append("model")
    if getattr(method, "_readonly", False):
        api.append("readonly")
    return api


def describe_model_doc(model):
    """The model's own docstring, rendered to HTML.

    Only classes that *are* this model count. Every mixin it inherits sits in
    the same MRO carrying its own ``_name`` and its own prose, and the first
    docstring found walking blindly is `mixin.mail.thread`'s far more often than the
    model's -- which would document Contact as "allow sending messages".

    :param model: a recordset
    :return: an HTML fragment, or None when the model documents itself nowhere
    :rtype: str | None
    """
    for cls in type(model).__mro__:
        if getattr(cls, "_name", None) != model._name:
            continue
        if doc := cls.__dict__.get("__doc__"):
            return render_docstring(doc)
    return None
