from ...fields.misc import Id
from ...fields.textual import Char
from ..metaclass import MetaModel
from ._metadata import _ModelMetadataMixin


class _MagicFieldsMixin(_ModelMetadataMixin, metaclass=MetaModel):
    __slots__ = ()

    _register = False

    id = Id()
    display_name = Char(
        compute="_compute_display_name",
        search="_search_display_name",
    )
