import sys

from style.styled_string_builder import _StyledStringBuilder


__version__ = '1.1.0'

_enabled = sys.stdout.isatty()
if '--color' in sys.argv:
    _enabled = True
elif '--no-color' in sys.argv:
    _enabled = False

styled_string_builder = _StyledStringBuilder([], True)
styled_string_builder.enabled = _enabled
styled_string_builder.__version__ = __version__
sys.modules[__name__] = styled_string_builder
