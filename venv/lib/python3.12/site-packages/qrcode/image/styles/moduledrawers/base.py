from __future__ import absolute_import

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qrcode.image.base import BaseImage


class QRModuleDrawer(abc.ABC):
    """
    QRModuleDrawer exists to draw the modules of the QR Code onto images.

    For this, technically all that is necessary is a ``drawrect(self, box,
    is_active)`` function which takes in the box in which it is to draw,
    whether or not the box is "active" (a module exists there). If
    ``needs_neighbors`` is set to True, then the method should also accept a
    ``neighbors`` kwarg (the neighboring pixels).

    It is frequently necessary to also implement an "initialize" function to
    set up values that only the containing Image class knows about.

    For examples of what these look like, see doc/module_drawers.png
    """

    needs_neighbors = False

    def __init__(self, **kwargs):
        pass

    def initialize(self, img: "BaseImage") -> None:
        self.img = img

    @abc.abstractmethod
    def drawrect(self, box, is_active) -> None:
        ...
