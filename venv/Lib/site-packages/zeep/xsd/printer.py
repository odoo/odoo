from collections import OrderedDict
from io import StringIO


class PrettyPrinter:
    """Cleaner pprint output.

    Heavily inspired by the Python pprint module, but more basic for now.

    """

    def pformat(self, obj):
        stream = StringIO()
        self._format(obj, stream)
        return stream.getvalue()

    def _format(self, obj, stream, indent=4, level=1):
        _repr = getattr(type(obj), "__repr__", None)
        write = stream.write

        if (isinstance(obj, dict) and _repr is dict.__repr__) or (
            isinstance(obj, OrderedDict) and _repr == OrderedDict.__repr__
        ):
            write("{\n")
            num = len(obj)

            if num > 0:
                for i, (key, value) in enumerate(obj.items()):
                    write(" " * (indent * level))
                    write("'%s'" % key)
                    write(": ")
                    self._format(value, stream, level=level + 1)
                    if i < num - 1:
                        write(",")
                    write("\n")

                write(" " * (indent * (level - 1)))
            write("}")

        elif isinstance(obj, list) and _repr is list.__repr__:
            write("[")
            num = len(obj)

            if num > 0:
                write("\n")
                for i, value in enumerate(obj):
                    write(" " * (indent * level))
                    self._format(value, stream, level=level + 1)
                    if i < num - 1:
                        write(",")
                    write("\n")
                write(" " * (indent * (level - 1)))
            write("]")
        else:
            value = repr(obj)
            if "\n" in value:
                lines = value.split("\n")
                num = len(lines)
                for i, line in enumerate(lines):
                    if i > 0:
                        write(" " * (indent * (level - 1)))
                    write(line)
                    if i < num - 1:
                        write("\n")
            else:
                write(value)
