
# For security and optimisation purpose we import only the necessary controllers
from odoo.addons.hw_drivers.tools.helpers import IS_BOX, get_odoo_server_url

from . import general
from . import drivers_settings
from . import list_handlers

if IS_BOX:
    from . import update
    from . import wifi
    from . import ssh

if get_odoo_server_url():
    from . import credential
    from . import six_payment_terminal
