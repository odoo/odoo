# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from ..core import AbstractComponent


class BaseComponent(AbstractComponent):
    """This is the base component for every component

    It is implicitely inherited by all components.

    All your base are belong to us
    """

    _name = "base"
