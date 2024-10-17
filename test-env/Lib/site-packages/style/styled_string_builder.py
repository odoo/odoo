import types

from style.ansi import _styles
from style.styled_string import _StyledString


_module_name = __name__.split('.')[0]


class _StyledStringBuilder(types.ModuleType):
    _enabled = True

    @property
    def enabled(self):
        return _StyledStringBuilder._enabled

    @enabled.setter
    def enabled(self, value):
        _StyledStringBuilder._enabled = value

    def __init__(self, style_list, is_root=False):
        super(_StyledStringBuilder, self).__init__(_module_name)
        self._style_list = style_list
        self._is_root = is_root

    def __call__(self, *objects, **kwargs):
        if self._is_root:
            raise TypeError('%r object is not callable' % self.__class__.__bases__[0].__name__)

        sep = kwargs.get('sep', ' ')
        if type(sep) is not str:
            raise TypeError('sep must be None or a string, not %r' % sep.__class__.__name__)

        return _StyledString(self._style_list, sep, *objects)

    def __getattr__(self, attr):
        if attr in _styles:
            if self._is_root:
                new_style_list = self._style_list[:]
                new_style_list.append(_styles[attr])
                return _StyledStringBuilder(new_style_list)
            self._style_list.append(_styles[attr])
            return self
        raise AttributeError('%r object has no attribute %r' % (self.__class__.__name__, attr))
