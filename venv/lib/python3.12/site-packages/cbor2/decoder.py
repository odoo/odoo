from warnings import warn

from ._decoder import CBORDecoder as CBORDecoder
from ._decoder import load as load
from ._decoder import loads as loads

warn("The cbor.decoder module has been deprecated. Instead import everything directly from cbor2.")
