from odoo.addons.component.core import Component


class WooModelBinder(Component):
    """
    Bind records and give odoo/woo ids correspondence
    Binding models are models called ``woo.{normal_model}``,
    like ``woo.res.partner``.
    They are ``_inherits`` of the normal models and contains
    the woo ID, the ID of the woo Backend and the additional
    fields belonging to the woo instance.
    """

    _name = "woo.binder"
    _inherit = ["base.binder", "connector.woo.base"]
    _apply_on = [
        "woo.res.partner",
        "woo.product.product",
        "woo.product.attribute",
        "woo.product.attribute.value",
        "woo.product.tag",
        "woo.sale.order",
        "woo.sale.order.line",
        "woo.product.category",
        "woo.delivery.carrier",
        "woo.res.country",
        "woo.settings",
        "woo.tax",
        "woo.payment.gateway",
        "woo.product.template",
        "woo.downloadable.product",
        "woo.stock.picking.refund",
    ]
