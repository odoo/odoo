from typing import Any

from ._decoder import CBORDecoder as CBORDecoder
from ._decoder import load as load
from ._decoder import loads as loads
from ._encoder import CBOREncoder as CBOREncoder
from ._encoder import dump as dump
from ._encoder import dumps as dumps
from ._encoder import shareable_encoder as shareable_encoder
from ._types import CBORDecodeEOF as CBORDecodeEOF
from ._types import CBORDecodeError as CBORDecodeError
from ._types import CBORDecodeValueError as CBORDecodeValueError
from ._types import CBOREncodeError as CBOREncodeError
from ._types import CBOREncodeTypeError as CBOREncodeTypeError
from ._types import CBOREncodeValueError as CBOREncodeValueError
from ._types import CBORError as CBORError
from ._types import CBORSimpleValue as CBORSimpleValue
from ._types import CBORTag as CBORTag
from ._types import FrozenDict as FrozenDict
from ._types import undefined as undefined

try:
    from _cbor2 import *  # noqa: F403
except ImportError:
    # Couldn't import the optimized C version; ignore the failure and leave the
    # pure Python implementations in place.

    # Re-export imports so they look like they live directly in this package
    key: str
    value: Any
    for key, value in list(locals().items()):
        if callable(value) and getattr(value, "__module__", "").startswith("cbor2."):
            value.__module__ = __name__
else:
    # The pure Python implementations are replaced with the optimized C
    # variants, but we still need to create the encoder dictionaries for the C
    # variant here (this is much simpler than doing so in C, and doesn't affect
    # overall performance as it's a one-off initialization cost).
    def _init_cbor2() -> None:
        from collections import OrderedDict

        import _cbor2

        from ._encoder import canonical_encoders, default_encoders
        from ._types import CBORSimpleValue, CBORTag, undefined

        _cbor2.default_encoders = OrderedDict(
            [
                (
                    (
                        _cbor2.CBORSimpleValue
                        if type_ is CBORSimpleValue
                        else _cbor2.CBORTag
                        if type_ is CBORTag
                        else type(_cbor2.undefined)
                        if type_ is type(undefined)
                        else type_
                    ),
                    getattr(_cbor2.CBOREncoder, method.__name__),
                )
                for type_, method in default_encoders.items()
            ]
        )
        _cbor2.canonical_encoders = OrderedDict(
            [
                (
                    (
                        _cbor2.CBORSimpleValue
                        if type_ is CBORSimpleValue
                        else _cbor2.CBORTag
                        if type_ is CBORTag
                        else type(_cbor2.undefined)
                        if type_ is type(undefined)
                        else type_
                    ),
                    getattr(_cbor2.CBOREncoder, method.__name__),
                )
                for type_, method in canonical_encoders.items()
            ]
        )

    _init_cbor2()
    del _init_cbor2
