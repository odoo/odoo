import types
from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Set,  # noqa: PYI025
)

import odoo.orm.table_objects
import odoo.tools
from odoo import fields
from odoo.tests import TransactionCase

# Can't use a set, because those types are not hashable. Use a tuple
# with the items sorted by occurence (most common first) to accelerate
# the O(n) lookup.
immutable_types = (
    types.FunctionType,                                         # 465218
    str,                                                         # 26711
    bool,                                                        # 17591
    property,                                                    # 14442
    types.NoneType,                                               # 5439
    types.MemberDescriptorType,                                   # 4311
    types.MethodType,                                             # 1489
    tuple,                                                        # 1398
    int,                                                           # 851
    odoo.orm.table_objects.Constraint,                             # 463
    odoo.orm.table_objects.Index,                                   # 74
    odoo.orm.table_objects.UniqueIndex,                             # 46
    float,                                                           # 6

    bytes,                                                           # 0
    complex,                                                         # 0
    frozenset,                                                       # 0
    range,                                                           # 0
    odoo.tools.frozendict,                                           # 0
    odoo.tools.misc.ReadonlyDict,                                    # 0
)
immutable_collections = (Sequence, Mapping, Set)
mutable_collections = (MutableSequence, MutableMapping, MutableSet)

FAIL_TEMPLATE = """Found mutable attributes in models.

Those are dangerous because they can be modified in unexpected ways by \
rogue users via safe_eval() and should either:

* Be replaced by immutable datatypes:
    list -> tuple
    set  -> frozenset
    dict -> odoo.tools.frozendict
* Be moved out of the class, by example to the global scope of the\
 python module;
* As last resort, be renamed with a double underscore suffix.

Found {} mutable attributes in models:

{}"""


class TestMutableClassAttr(TransactionCase):
    def test_mutable_class_attr(self):
        seen = set()
        for cls in self.env.registry.values():
            for attr_name in dir(cls):
                if '__' in attr_name:
                    continue
                attr_type = type(getattr(cls, attr_name))
                if attr_type in immutable_types:
                    continue
                if (
                    attr_type.__module__.startswith('odoo.orm.fields')
                    or issubclass(attr_type, fields.Field)
                ):
                    continue
                if (
                    issubclass(attr_type, immutable_collections)
                    and not issubclass(attr_type, mutable_collections)
                ):
                    continue
                for base_cls in reversed(cls.mro()):
                    if (str(base_cls), attr_name) in seen:
                        break
                    if hasattr(base_cls, attr_name):
                        seen.add((str(base_cls), attr_name))
                        break

        if seen:
            pass
            self.fail(FAIL_TEMPLATE.format(
                len(seen),
                '\n'.join('%s %s' % item for item in sorted(seen)),
            ))
