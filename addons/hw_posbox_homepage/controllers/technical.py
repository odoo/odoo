
from dataclasses import dataclass
from sys import modules

from odoo.addons.hw_posbox_homepage.controllers.jinja import add_jinja_globals


@dataclass
class TechnicalMenu:
    """Define a technical menu for the IoT technical page"""
    name: str
    """Name of the (sub)menu as it will appear in the IoT technical page dropdown"""
    url: str
    """URL of the (sub)menu"""
    module_name: str
    """Name of the python module that contains the controller for the (sub)menu"""
    sub_menus: tuple['TechnicalMenu', ...] = tuple()
    """Submenus of the (sub)menu"""

    _is_active: bool = None
    """cached value of `is_active` property"""

    def __post_init__(self):
        _TECHNICAL_MENUS_BY_MODULE_NAME[self.module_name] = self

    # defer the check of the module activation as `sys.modules` is not fully loaded at the time of the creation
    @property
    def is_active(self):
        """Check if the module is active or not.
        It might be not active if it was disabled for a given IoT type
        (e.g: Windows Virtual IoT does not need to set wifi unlike IoT Box)
        """
        if self._is_active is None:
            technical_module_name = 'odoo.addons.hw_posbox_homepage.controllers.technicals.' + self.module_name
            self._is_active = technical_module_name in modules
        return self._is_active


_TECHNICAL_MENUS_BY_MODULE_NAME = {}

TECHNICAL_MENUS = TechnicalMenu('MAIN', None, 'dummy', (  # abstract menu
    TechnicalMenu('General', '/technical', 'general', (
        TechnicalMenu('Version Update', '/hw_proxy/upgrade', 'update'),
        TechnicalMenu('Network Configuration', '/wifi', 'wifi'),
    )),
    TechnicalMenu('Credentials', '/list_credential', 'credential'),
    TechnicalMenu('Drivers Settings', '/technical/driver_settings', 'drivers_settings', (
        TechnicalMenu('SIX Payment Terminal', '/six_payment_terminal', 'six_payment_terminal'),
    )),
    TechnicalMenu('Handlers List', '/list_handlers', 'list_handlers'),
    TechnicalMenu('SSH / Remote Access', '/technical/ssh', 'ssh'),
))


add_jinja_globals({'TECHNICAL_MENUS': TECHNICAL_MENUS})


def get_technical_menu_by_module_name(module_name: str) -> TechnicalMenu:
    """Get the technical menu by its module name"""
    return _TECHNICAL_MENUS_BY_MODULE_NAME[module_name]
