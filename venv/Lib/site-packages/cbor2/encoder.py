from warnings import warn

from ._encoder import CBOREncoder as CBOREncoder
from ._encoder import dump as dump
from ._encoder import dumps as dumps
from ._encoder import shareable_encoder as shareable_encoder

warn(
    "The cbor2.encoder module has been deprecated. Instead import everything directly from cbor2."
)
