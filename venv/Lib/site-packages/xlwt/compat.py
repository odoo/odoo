import sys

PY3 = sys.version_info[0] >= 3

if PY3:
    unicode = bytes.decode
    unicode_type = str
    basestring = str
    xrange = range
    int_types = (int,)
    long = int

    def iteritems(d):
        return iter(d.items())
    def itervalues(d):
        return iter(d.values())
else:
    # Python 2
    unicode = unicode_type = unicode
    basestring = basestring
    xrange = xrange
    int_types = (int, long)
    long = long

    def iteritems(d):
        return d.iteritems()
    def itervalues(d):
        return d.itervalues()
