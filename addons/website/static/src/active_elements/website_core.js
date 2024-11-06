import { registry } from "@web/core/registry";
import { _t, translationIsReady } from "@web/core/l10n/translation";
import { App, Component } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";

/**
 * Website Core
 * 
 * This service handles the core interactions for the website codebase.
 * It will replace public root, publicroot instance, and all that stuff
 *
 * To add a component into the website, we have two possibilities:
 * - a mounted component in a selector
 * - an attached component in a selector
 * 
 * Each of them is for a different usecase:
 * - mounting component in a selector: this is useful for adding complex behavior
 *   that can be displayed later, when it is ready. For example, the livechat
 * - attaching component in a selector: this is useful to add behavior to a
 *   server rendered html element.  For exemple, a form.
 */

const activeElementRegistry = registry.category("website.active_elements");

class WebsiteCore {
    constructor(env) {
        this.env = env;
        this.interactions = {};
        this.roots = [];
        const appConfig = {
            name: "Odoo Website",
            getTemplate,
            env: env,
            dev: env.debug,
            translateFn: _t,
            warnIfNoStaticProps: env.debug,
            translatableAttributes: ["data-tooltip"],
        };
        this.app = new App(null, appConfig);
        this.startInteractions();
    }

    _startInteraction(name, C) {
        for (let el of document.querySelectorAll(C.selector)) {
            // C is either a simple Interaction or a Component class
            if (C.prototype instanceof Component) {
                const mode = C.template ? "standard" : (C.dynamicContent ? "attached" : null);
                if (!mode) {
                    throw new Error("Component does not have a template or a dynamicContent description");
                }
                console.log("Starting component", name);
                const root = this.app.createRoot(C, { props: null, env: this.env});
                this.roots.push(root);
                if (mode === "standard") {
                    const compElem = document.createElement("owl-component");
                    compElem.setAttribute("contenteditable", "false");
                    compElem.dataset.oeProtected = "true";
                    el.appendChild(compElem);
                    // note that it is async!
                    root.mount(compElem);
                } else {
                    root.mount(el, { position: "attach" });
                }
            } else {
                throw new Error("Invalid interaction: should be a component");
            }
        }
    }

    startInteractions() {
        for (const [name, E] of activeElementRegistry.getEntries()) {
            this._startInteraction(name, E);
        }
        activeElementRegistry.addEventListener("UPDATE", async (ev) => {
            const { operation, key: name, value: I } = ev.detail;
            if (operation !== "delete") {
                this._startInteraction(name, I);
            }
        });
    }

    stopInteractions() {
        for (let root of this.roots) {
            root.destroy();
        }
    }
}

registry.category("services").add("website_core", {
    async start(env) {
        // only temporary! need to do better!
        // @todo: remove this
        await translationIsReady;
        return new WebsiteCore(env);
    }
});