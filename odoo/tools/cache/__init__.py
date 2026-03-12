import warnings
warnings.warn("Since 20.0 import ormcache from odoo.api", DeprecationWarning)  # noqa: RUF067
from odoo.orm.cache import *  # noqa: E402, F403
