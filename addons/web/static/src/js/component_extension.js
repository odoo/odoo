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
                    if (!this.__owl__.isDestroyed) {
                        resolve(result);
                    }
                })
                .catch(reason => {
                    if (!this.__owl__.isDestroyed) {
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

    /**
     * Patch owl.Component.willStart method to handle xmlDependencies class
     * member, i.e. to lazy load templates. It may prove useful for Odoo's
     * frontend.
     */
    const originalWillStart = owl.Component.prototype.willStart;
    owl.Component.prototype.willStart = async function() {
        const constructor = this.constructor;
        const proms = [];
        const unknownTemplate = !(constructor.template in this.env.qweb.templates);
        if (unknownTemplate && this.constructor.xmlDependencies) {
            const templateProm = this.env.services.ajax.loadOwlXML(constructor.xmlDependencies);
            templateProm.then(results => {
                for (const doc of results) {
                    const frag = document.createElement('t');
                    frag.innerHTML = doc;
                    for (let child of frag.querySelectorAll("templates > [t-name][owl]")) {
                        child.removeAttribute('owl');
                        const name = child.getAttribute("t-name");
                        this.env.qweb.addTemplate(name, child.outerHTML, true);
                    }
                }
            });
            proms.push(templateProm);
        }
        if (constructor.jsLibs || constructor.cssLibs || constructor.assetLibs) {
            const libs = {
                jsLibs: constructor.jsLibs,
                cssLibs: constructor.cssLibs,
                assetLibs: constructor.assetLibs,
            }
            proms.push(this.env.services.ajax.loadLibs(libs));
        }
        await Promise.all(proms);
        return originalWillStart.apply(this, ...arguments);
    };
})();
