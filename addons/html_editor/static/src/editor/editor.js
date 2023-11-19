/** @odoo-module */

/**
 * @typedef {typeof import("./plugin").Plugin} PluginConstructor
 */

export class Editor {
    /**
     * @param {PluginConstructor[]} Plugins
     * @param {*} config
     * @param {*} services
     */
    constructor(Plugins, config, services) {
        this.Plugins = Plugins;
        this.config = config;
        this.services = services;
        this.plugins = [];
        this.el = null;
    }

    attachTo(el) {
        this.el = el;
        if (this.config.innerHTML) {
            el.innerHTML = this.config.innerHTML;
        }
        el.setAttribute("contenteditable", true);
        el.classList.add("odoo-editor-editable");
        this.startPlugins();
    }

    startPlugins() {
        const plugins = new Map();
        const shared = {};
        // const dispatch = this.dispatch.bind(this);
        for (const P of this.Plugins) {
            if (P.name === "") {
                throw new Error(`Missing plugin name (class ${P.constructor.name})`);
            }
            if (plugins.has(P.name)) {
                throw new Error(`Duplicate plugin name: ${P.name}`);
            }
            const _shared = {};
            for (const dep of P.dependencies) {
                if (plugins.has(dep)) {
                    for (const h of plugins.get(dep).shared) {
                        _shared[h] = shared[h];
                    }
                } else {
                    throw new Error(`Missing dependency for plugin ${P.name}: ${dep}`);
                }
            }
            plugins.set(P.name, P);
            // debug
            const dispatch = (command, payload) => {
                let str = payload;
                if (typeof payload === "object") {
                    str = JSON.stringify(payload);
                }
                console.log(`[${P.name}] ${command} (payload=${str})`);
                this.dispatch(command, payload);
            };
            const plugin = new P(this.el, _shared, dispatch, this.config, this.services);
            this.plugins.push(plugin);
            for (const h of P.shared) {
                if (h in shared) {
                    throw new Error(`Duplicate shared name: ${h}`);
                }
                if (!(h in plugin)) {
                    throw new Error(`Missing helper implementation: ${h} in plugin ${P.name}`);
                }
                shared[h] = plugin[h].bind(plugin);
            }
        }
    }

    dispatch(command, payload = {}) {
        if (!this.el) {
            throw new Error("Cannot dispatch command while not attached to an element");
        }
        for (const p of this.plugins) {
            p.handleCommand(command, payload);
        }
    }

    destroy() {
        if (this.el) {
            this.el.removeAttribute("contenteditable");
            this.el.classList.remove("odoo-editor-editable");
            for (const p of this.plugins) {
                p.destroy();
            }
            this.el = null;
        }
    }
}
