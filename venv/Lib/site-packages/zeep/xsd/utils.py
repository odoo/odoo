from zeep import ns


class NamePrefixGenerator:
    def __init__(self, prefix="_value_"):
        self._num = 1
        self._prefix = prefix

    def get_name(self):
        retval = "%s%d" % (self._prefix, self._num)
        self._num += 1
        return retval


class UniqueNameGenerator:
    def __init__(self):
        self._unique_count = {}

    def create_name(self, name):
        if name in self._unique_count:
            self._unique_count[name] += 1
            return "%s__%d" % (name, self._unique_count[name])
        else:
            self._unique_count[name] = 0
            return name


def max_occurs_iter(max_occurs, items=None):
    assert max_occurs is not None
    generator = range(0, max_occurs if max_occurs != "unbounded" else 2**31 - 1)

    if items is not None:
        for i, sub_kwargs in zip(generator, items):
            yield sub_kwargs
    else:
        for i in generator:
            yield i


def create_prefixed_name(qname, schema):
    """Convert a QName to a xsd:name ('ns1:myType').

    :type qname: lxml.etree.QName
    :type schema: zeep.xsd.schema.Schema
    :rtype: str

    """
    if not qname:
        return

    if schema and qname.namespace:
        prefix = schema.get_shorthand_for_ns(qname.namespace)
        if prefix:
            return "%s:%s" % (prefix, qname.localname)
    elif qname.namespace in ns.NAMESPACE_TO_PREFIX:
        prefix = ns.NAMESPACE_TO_PREFIX[qname.namespace]
        return "%s:%s" % (prefix, qname.localname)

    if qname.namespace:
        return qname.text
    return qname.localname
