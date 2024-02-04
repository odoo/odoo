from odoo.tools import config

from . import models

if not config.get("without_demo"):
    from . import demo
