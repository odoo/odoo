# Use this folder to add any temporary fixes to the strdnum library.
# Please add a comment in the related files mentionning the fixing commit and
# the version where it is fixed in stdnum
# If it is not fixed yet, please open an Issue on their side and add the link
# to that issue instead
# Please also provide a test for a failing/passing number in `test_all_formats`

# The version of stdnum used by Odoo is the older version between the LTS
# Ubuntu and the LTS Debian at the release time of the Odoo major version.
# It is now on version 1.13
import stdnum
import logging
from inspect import currentframe

def check_stdnum_version(version):
    if version < stdnum.__version__:
        _logger = logging.getLogger(currentframe().f_back.f_globals['__name__'])
        _logger.warning(
            "Useless override of stdnum (version %s), fixed in %s",
            stdnum.__version__,
            version,
        )

from . import (
    au,
    # ch,
    ec,
    # ie,
    in_,
    # mx,
    # nl,
    # no,
    pe,
    # ru,
    tr,
    ua,
    xi,
)
