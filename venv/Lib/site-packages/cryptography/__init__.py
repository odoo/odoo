# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

import sys
import warnings

from cryptography.__about__ import __author__, __copyright__, __version__
from cryptography.utils import CryptographyDeprecationWarning

__all__ = [
    "__version__",
    "__author__",
    "__copyright__",
]

if sys.version_info[:2] == (3, 6):
    warnings.warn(
        "Python 3.6 is no longer supported by the Python core team. "
        "Therefore, support for it is deprecated in cryptography. The next "
        "release of cryptography (40.0) will be the last to support Python "
        "3.6.",
        CryptographyDeprecationWarning,
        stacklevel=2,
    )
