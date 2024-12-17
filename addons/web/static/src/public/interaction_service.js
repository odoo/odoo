import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Interaction } from "./interaction";
import { getTemplate } from "@web/core/templates";
import { PairSet } from "./utils";
import { Colibri } from "./colibri";

/**
 * Website Core
 *
 * This service handles the core interactions for the website codebase.
 * It will replace public root, publicroot instance, and all that stuff
 *
 * We have 2 kinds of interactions:
 * - simple interactions (subclasses of Interaction)
 * - components
 *
 * The Interaction class is designed to be a simple class that provides access
 * to the framework (env and services), and a minimalist declarative framework
 * that allows manipulating dom, attaching event handlers and updating it
 * properly. It does not depend on owl.
 *
 * The Component kind of interaction is used for more complicated interface needs.
 * It provides full access to Owl features, but is rendered browser side.
 *
 */

class InteractionService {
    /**
     *
     * @param {HTMLElement} el
     * @param {Object} env
     */
    constructor(el, env) {
        this.Interactions = [];
        this.el = el;
        this.isActive = false;
        // relation el <--> Interaction
        this.activeInteractions = new PairSet();
        this.env = env;
        this.interactions = [];
        this.roots = [];
        this.owlApp = null;
        this.proms = [];
        this.registry = null;
    }

    /**
     *
     * @param {Interaction[]} Interactions
     */
    activate(Interactions) {
        this.Interactions = Interactions;
        const startProm = this.env.isReady.then(() => this.startInteractions());
        this.proms.push(startProm);
    }

    prepareRoot(el, C, props) {
        if (!this.owlApp) {
            const { App } = odoo.loader.modules.get("@odoo/owl");
            const appConfig = {
                name: "Odoo Website",
                getTemplate,
                env: this.env,
                dev: this.env.debug,
                translateFn: _t,
                warnIfNoStaticProps: this.env.debug,
                translatableAttributes: ["data-tooltip"],
            };
            this.owlApp = new App(null, appConfig);
        }
        const root = this.owlApp.createRoot(C, { props, env: this.env });
        const compElem = document.createElement("owl-component");
        compElem.setAttribute("contenteditable", "false");
        compElem.dataset.oeProtected = "true";
        el.appendChild(compElem);
        return {
            C,
            root,
            el: compElem,
            mount: () => root.mount(compElem),
            destroy: () => {
                root.destroy();
                compElem.remove();
            },
        };
    }

    async _mountComponent(el, C) {
        const root = this.prepareRoot(el, C);
        this.roots.push(root);
        return root.mount();
    }

    startInteractions(el = this.el) {
        const proms = [];
        for (const I of this.Interactions) {
            if (I.selector === "") {
                throw new Error(
                    `The selector should be defined as a static property on the class ${I.name}, not on the instance`
                );
            }
            if (I.dynamicContent) {
                throw new Error(
                    `The dynamic content object should be defined on the instance, not on the class (${I.name})`
                );
            }
            if (el.matches(I.selector)) {
                this._startInteraction(el, I, proms);
            } else {
                for (const _el of el.querySelectorAll(I.selector)) {
                    this._startInteraction(_el, I, proms);
                }
            }
        }
        if (el === this.el) {
            this.isActive = true;
        }
        const prom = Promise.all(proms);
        this.proms.push(prom);
        return prom;
    }

    _startInteraction(el, I, proms) {
        if (this.activeInteractions.has(el, I)) {
            return;
        }
        this.activeInteractions.add(el, I);
        if (I.prototype instanceof Interaction) {
            try {
                // console.log(`[colibri] starting ${I.name}`);
                const interaction = new Colibri(this, I, el);
                this.interactions.push(interaction);
                proms.push(interaction.start());
            } catch (e) {
                this.proms.push(Promise.reject(e));
            }
        } else {
            proms.push(this._mountComponent(el, I));
        }
    }

    stopInteractions(el = this.el) {
        const interactions = [];
        for (const interaction of this.interactions.slice().reverse()) {
            if (el === interaction.el || el.contains(interaction.el)) {
                // console.log(`[colibri] stopping ${interaction.interaction.constructor.name}`);
                interaction.destroy();
                this.activeInteractions.delete(interaction.el, interaction.interaction.constructor);
            } else {
                interactions.push(interaction);
            }
        }
        this.interactions = interactions;
        const roots = [];
        for (const root of this.roots.slice().reverse()) {
            if (el === root.el || el.contains(root.el)) {
                root.destroy();
                this.activeInteractions.delete(root.el, root.C);
            } else {
                roots.push(root);
            }
        }
        this.roots = roots;
        if (el === this.el) {
            this.isActive = false;
        }
    }

    /**
     * @returns { Promise } returns a promise that is resolved when all current
     * interactions are started. Note that it does not take into account possible
     * future interactions.
     */
    get isReady() {
        const proms = this.proms.slice();
        return Promise.all(proms);
    }
}

registry.category("services").add("public.interactions", {
    dependencies: ["localization"],
    async start(env) {
        const el = document.querySelector("#wrapwrap");
        if (!el) {
            // if this is an issue, maybe we should make the wrapwrap configurable
            return null;
        }
        const Interactions = registry.category("public.interactions").getAll();
        const service = new InteractionService(el, env);
        service.activate(Interactions);
        return service;
    },
});
