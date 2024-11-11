/**
 * This is the base class to describe interactions. It contains a few helper
 * to accomplish common tasks, such as adding dom listener or waiting for 
 * some task to complete
 */
export class Interaction {
    static selector = "";

    constructor(el, env, metadata) {
        this.__colibri__ = metadata;
        this.isDestroyed = false;
        this.el = el;
        this.env = env;
        this.services = env.services;
    }

    // -------------------------------------------------------------------------
    // lifecycle methods
    // -------------------------------------------------------------------------
    setup() {}

    async willStart() {}

    start() {}

    destroy() {}

    // -------------------------------------------------------------------------
    // helpers
    // -------------------------------------------------------------------------
    waitFor(fn) {
        return new Promise(async (resolve) => {
            const result = await fn();
            if (!this.isDestroyed) {
                resolve(result);
                this.updateDOM();
            }
        });
    }

    updateDOM() {
        this.__colibri__.scheduleUpdate();
    }

    addDomListener(target, event, fn, options) {
        const nodes = typeof target === "string" ? this.el.querySelectorAll(target) : [target];
        this.__colibri__.addDomListener(nodes, event, fn, options);
    }

    mountComponent() {
        // todo
    }

}
