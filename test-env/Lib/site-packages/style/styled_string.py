import style


class _StyledString(str):

    def __new__(cls, style_list, sep, *objects):
        return super(_StyledString, cls).__new__(cls, sep.join([str(obj) for obj in objects]))

    def __init__(self, style_list, sep, *objects):
        self._style_start = ';'.join([str(s[0]) for s in style_list])
        self._style_end = ';'.join([str(s[1]) for s in style_list])
        self._sep = sep
        self._objects = objects

    def __add__(self, other):
        return self.__str__() + str(other)

    def __str__(self):
        if style._StyledStringBuilder._enabled:
            string = ''
            for i, obj in enumerate(self._objects):
                if i > 0:
                    string += self._sep

                if type(obj) is _StyledString:
                    string += '%s\033[%sm' % (obj, self._style_start)
                else:
                    string += str(obj)
            return '\033[%sm%s\033[%sm' % (self._style_start, string, self._style_end)
        return super(_StyledString, self).__str__()
