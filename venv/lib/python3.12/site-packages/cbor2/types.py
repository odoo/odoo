from warnings import warn

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

warn("The cbor2.types module has been deprecated. Instead import everything directly from cbor2.")
