from odoo.addons.component.core import AbstractComponent


class ConnectorWooBaseComponent(AbstractComponent):
    """
    Base woocommerce Connector Component
    All components of this connector should inherit from it.
    """

    _name = "connector.woo.base"
    _inherit = "base.connector"
    _collection = "woo.backend"
