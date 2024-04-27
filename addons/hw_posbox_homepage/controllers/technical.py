
from dataclasses import dataclass
from importlib import import_module
from platform import system

import logging

from odoo.http import request
from odoo.addons.hw_posbox_homepage.controllers.jinja import jinja_env
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)

# Constant conditions (can't chagne without an IoT restart)
IS_LINUX = system() == 'Linux'
SERVER_URL = helpers.get_odoo_server_url()


@dataclass
class TechnicalMenu:
    """Define a Technical Menu for the IoT Box Technical Page"""
    TECHNICAL_MENUS_CONTROLLER_MODULE_PATH = '.'.join(__name__.split('.')[:-1] + ['technicals', '%s'])

    name: str
    url: str
    view_controller_file_name: str
    """View and Controller file name of the menu.
    The name should exists in both controllers/technicals folder and views/technical folder"""
    sub_menus: tuple = ()
    parent: 'TechnicalMenu' = None

    def __post_init__(self):
        self.sub_menus = tuple(filter(None, self.sub_menus))
        self.jinja_template = self.view_controller_file_name and jinja_env.get_template(f'technical/{self.view_controller_file_name}.jinja2')

    def load_controller(self, parent=None):
        """Load the controller of the menu and its submenus. Also set the parent menu."""
        if self.view_controller_file_name:
            future_addons_module_name = self.TECHNICAL_MENUS_CONTROLLER_MODULE_PATH % self.view_controller_file_name
            _logger.info("loading dynamically technical controller %s", future_addons_module_name)
            _TECHNICAL_MENUS_MODULE_MENU[future_addons_module_name] = self
            import_module(future_addons_module_name)

        for menu in self.sub_menus:
            menu.load_controller(parent)

    def get_submenu(self, submenu_name):
        for menu in self.sub_menus:
            if menu.name == submenu_name:
                return menu

    def get_submenu_url(self, submenu_name):
        sub_menu = self.get_submenu(submenu_name)
        return sub_menu and sub_menu.url


class IoTTechnicalPage:
    # Note, we pusposfully don't inherit from Controller due to odoo.http overriden inheristance system.
    # Overriding `__init__` with `self.__name__` will always give `odoo.http` instead of the technical module name
    """Abstract base class for all IoT Box Technical Pages."""
    _menu: TechnicalMenu = None

    def render(self, **kwargs):
        return self._menu.jinja_template.render({
            'title': "Odoo's IoT Box - Technical",
            'breadcrumb': 'Technical',
            'TECHNICAL_MENUS': TECHNICAL_MENUS,
            'request_path': request.httprequest.path,
            **kwargs
        })


_TECHNICAL_MENUS_MODULE_MENU: dict = {}


def get_menu(module_name) -> TechnicalMenu:
    """Get the Technical Menu of the given the technical module name."""
    return _TECHNICAL_MENUS_MODULE_MENU[module_name]


TECHNICAL_MENUS = TechnicalMenu('MAIN', None, None, (  # abstract menu
    TechnicalMenu('General', '/technical', 'general', (
        TechnicalMenu('Version Update', '/hw_proxy/upgrade', 'update') if IS_LINUX else None,
        TechnicalMenu('Network Configuration', '/wifi', 'wifi') if IS_LINUX else None,
    )),
    TechnicalMenu('Credentials', '/list_credential', 'credential') if bool(SERVER_URL) else None,
    TechnicalMenu('Drivers Settings', '/technical/driver_settings', 'drivers_settings', (
        TechnicalMenu('SIX Payment Terminal', '/six_payment_terminal', 'six_payment_terminal') if SERVER_URL else None,
    )),
    TechnicalMenu('Handlers List', '/list_handlers', 'list_handlers'),
    TechnicalMenu('SSH / Remote Access', '/technical/ssh', 'ssh') if IS_LINUX else None,
))

TECHNICAL_MENUS.load_controller()  # Load all controllers by loading the main menu
