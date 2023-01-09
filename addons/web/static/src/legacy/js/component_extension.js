(function () {

    owl.Component.env = {};

    /**
     * Symbol used in ComponentWrapper to redirect Owl events to Odoo legacy
     * events.
     */
    odoo.widgetSymbol = Symbol('widget');
})();
