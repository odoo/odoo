# Compatibility shim — float_utils moved to odoo.libs.numbers.float_utils
# Keep this so enterprise and third-party addons using the old import path continue to work.
from odoo.libs.numbers.float_utils import *  # noqa: F403
from odoo.libs.numbers.float_utils import (
    round,
)
