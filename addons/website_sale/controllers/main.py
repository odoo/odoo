# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.checkout.address import Address
from odoo.addons.website_sale.controllers.checkout.checkout import Checkout
from odoo.addons.website_sale.controllers.checkout.confirmation import Confirmation
from odoo.addons.website_sale.controllers.checkout.extra_info import ExtraInfo
from odoo.addons.website_sale.controllers.checkout.payment import Payment
from odoo.addons.website_sale.controllers.editor import Editor
from odoo.addons.website_sale.controllers.product import Product
from odoo.addons.website_sale.controllers.shop import Shop


class WebsiteSale(Shop, Product, Address, Checkout, ExtraInfo, Payment, Confirmation, Editor):
    """Canonical composition of the eCommerce controller mixins.

    This class exists so that every module needing to override methods from more than one
    mixin (Shop, Product, Address, Checkout, ExtraInfo, Payment, Confirmation, Editor) extends
    THIS single class rather than combining an arbitrary subset of mixins itself. Odoo merges
    all controller "leaves" reachable from a shared root into a single dynamically-built class;
    if two unrelated modules combined the same mixins in different orders, that merge would fail
    with an inconsistent MRO. Routing through one fixed, canonical order here avoids that.
    """
