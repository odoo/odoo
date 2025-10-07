# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)


class ComponentException(Exception):
    """Base Exception for the components"""


class NoComponentError(ComponentException):
    """No component has been found"""


class SeveralComponentError(ComponentException):
    """More than one component have been found"""


class RegistryNotReadyError(ComponentException):
    """Component registry not ready yet for given DB."""
