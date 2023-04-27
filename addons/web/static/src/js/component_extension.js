(function () {
    /**
     * Symbol used in ComponentWrapper to redirect Owl events to Odoo legacy
     * events.
     */
    odoo.widgetSymbol = Symbol('widget');

    /**
     * Add a new method to owl Components to ensure that no performed RPC is
     * resolved/rejected when the component is destroyed.
     */
    owl.Component.prototype.rpc = function () {
        return new Promise((resolve, reject) => {
            return this.env.services.rpc(...arguments)
                .then(result => {
                    if (this.__owl__.status !== 5 /* not destroyed */) {
                        resolve(result);
                    }
                })
                .catch(reason => {
                    if (this.__owl__.status !== 5) /* not destroyed */ {
                        reject(reason);
                    }
                });
        });
    };

    /**
     * Patch owl.Component.__trigger method to call a hook that adds a listener
     * for the triggered event just before triggering it. This is useful if
     * there are legacy widgets in the ancestors. In that case, there would be
     * a widgetSymbol key in the environment, corresponding to the hook to call
     * (see ComponentWrapper).
     */
    const originalTrigger = owl.Component.prototype.__trigger;
    owl.Component.prototype.__trigger = function (component, evType, payload) {
        if (this.env[odoo.widgetSymbol]) {
            this.env[odoo.widgetSymbol](evType);
        }
        originalTrigger.call(this, component, evType, payload);
    };
})();
