import sys

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str

    def iteritems(d, **kw):
        return iter(d.items(**kw))
else:
    string_types = basestring

    def iteritems(d, **kw):
        return iter(d.iteritems(**kw))
