import { Scope, useApp, useScope } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { addLoadingEffect, isClickable } from "@web/core/utils/ui";
import { Colibri } from "./colibri";
import { Interaction } from "./interaction";
import lazyloader from "./lazyloader";
import { BUTTON_HANDLER_SELECTOR, PairSet } from "./utils";

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
 * properly. ~~It does not depend on owl~~.
 *                     ^^^
 * Edit: this commit added the explicit dependency to Owl, because it already depended
 * on it through @web/core/registry. Furthermore, 'prepareRoot' does NOT work without
 * an Owl App instance.
 *
 * The Component kind of interaction is used for more complicated interface needs.
 * It provides full access to Owl features, but is rendered browser side.
 *
 */
const waitForInteractionsSetup = Promise.withResolvers();
lazyloader.registerPageReadinessDelay(waitForInteractionsSetup.promise);

class InteractionScope extends Scope {}

class InteractionService {
    /**
     *
     * @param {HTMLElement} el
     * @param {Object} env
     */
    constructor(el, env) {
        this.scope = useScope();
        this.Interactions = [];
        this.el = el;
        this.isActive = false;
        this.initialSetupDone = false;
        // relation el <--> Interaction
        this.activeInteractions = new PairSet();
        this.env = env;
        this.interactions = [];
        this.roots = [];
        this.owlApp = useApp();
        this.proms = [];
        this.registry = null;
        this.shouldBuffer = false;
        this.bufferedClicks = new Map();
        this.bufferTargets = new Map();
    }

    /**
     *
     * @param {Interaction[]} Interactions
     * @param {HTMLElement} target - The target element where interactions need
     *                               to be activated.
     */
    activate(Interactions, target) {
        this.Interactions = Interactions;
        const startProm = this.scope.ready.then(async () => {
            const allInteractionsStarted = this.startInteractions(target);
            this.retriggerBufferedClicks();
            await allInteractionsStarted;
            this.shouldBuffer = false;
        });
        this.proms.push(startProm);
    }

    createInteractionScope() {
        return new InteractionScope(this.owlApp);
    }

    prepareRoot(el, C, props, position = "beforeend") {
        const root = this.owlApp.createRoot(C, { props, env: this.env });
        const rootEl = el.ownerDocument.createElement("owl-root");
        rootEl.setAttribute("contenteditable", "false");
        rootEl.dataset.oeProtected = "true";
        rootEl.style.display = "contents";
        el.insertAdjacentElement(position, rootEl);
        return {
            C,
            root,
            el: rootEl,
            mount: () => root.mount(rootEl),
            destroy: () => {
                root.destroy();
                rootEl.remove();
            },
        };
    }

    async _mountComponent(el, C) {
        const root = this.prepareRoot(el, C);
        this.roots.push(root);
        return root.mount();
    }

    startInteractions(el = this.el) {
        if (!el.isConnected) {
            return Promise.resolve();
        }
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
            let targets;
            try {
                const isMatch = el.matches(I.selector);
                targets = isMatch
                    ? [el, ...el.querySelectorAll(I.selector)]
                    : el.querySelectorAll(I.selector);
                if (I.selectorHas) {
                    if (!Array.isArray(I.selectorHas)) {
                        I.selectorHas = [I.selectorHas];
                    }
                    targets = [...targets].filter((el) =>
                        I.selectorHas.every((sel) => !!el.querySelector(`:scope ${sel}`))
                    );
                }
                if (I.selectorNotHas) {
                    if (!Array.isArray(I.selectorNotHas)) {
                        I.selectorNotHas = [I.selectorNotHas];
                    }
                    targets = [...targets].filter(
                        (el) =>
                            !I.selectorNotHas.every((sel) => !!el.querySelector(`:scope ${sel}`))
                    );
                }
            } catch {
                const selectorHasError = I.selectorHas
                    ? ` or selectorHas: '${I.selectorHas.join("', '")}'`
                    : "";
                const selectorNotHasError = I.selectorNotHas
                    ? ` or selectorNotHas: '${I.selectorNotHas.join("', '")}'`
                    : "";
                const error = new Error(
                    `Could not start interaction ${I.name} (invalid selector: '${I.selector}'${selectorHasError}${selectorNotHasError})`
                );
                proms.push(Promise.reject(error));
                continue;
            }
            for (const _el of targets) {
                this._startInteraction(_el, I, proms);
            }
        }
        if (!this.initialSetupDone) {
            waitForInteractionsSetup.resolve();
            this.shouldBuffer = true;
            this.initialSetupDone = true;
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
                const interaction = new Colibri(this, I, el);
                this.interactions.push(interaction);
                proms.push(interaction.start());
                this.registerBufferedClicks(interaction);
            } catch (e) {
                this.proms.push(Promise.reject(e));
            }
        } else {
            proms.push(this._mountComponent(el, I));
        }
    }

    shouldStop(el, interaction) {
        const { selectorNotHas, selectorHas } = interaction.interaction.constructor;
        if (!interaction.el) {
            return true;
        }
        const selectorHasArray = Array.isArray(selectorHas) ? selectorHas : [selectorHas];
        const selectorNotHasArray = Array.isArray(selectorNotHas)
            ? selectorNotHas
            : [selectorNotHas];
        return (
            el === interaction.el ||
            el.contains(interaction.el) ||
            (selectorHas &&
                selectorHasArray.some((sel) => !interaction.el.querySelector(`:scope ${sel}`))) ||
            (selectorNotHas &&
                selectorNotHasArray.some((sel) => !!interaction.el.querySelector(`:scope ${sel}`)))
        );
    }

    stopInteractions(el = this.el) {
        const interactions = [];
        const errors = [];
        for (const interaction of this.interactions.slice().reverse()) {
            if (this.shouldStop(el, interaction)) {
                try {
                    this.unbufferClicks(el, interaction);
                    interaction.destroy();
                } catch (error) {
                    errors.push([interaction.interaction.constructor.name, error]);
                }
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
        for (const [interaction, error] of errors) {
            throw new Error(`Could not destroy interaction ${interaction}`, error);
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

    /**************************** BUFFERING CLICKS ****************************/
    /**
     * Buffers clicks made before interactions are started to be replayed after.
     *
     * @param {Object} interaction - Colibri instance
     */
    registerBufferedClicks(interaction) {
        const btnEls = [];
        const dynamicContent = interaction.interaction.dynamicContent;
        for (const sel in dynamicContent) {
            const hasClickListener = Object.keys(dynamicContent[sel]).some((directive) =>
                directive.startsWith("t-on-click")
            );
            if (hasClickListener) {
                const nodes = interaction.getNodes(sel);
                btnEls.push(
                    ...nodes.filter(
                        (node) => node.nodeType === 1 && node.matches(BUTTON_HANDLER_SELECTOR)
                    )
                );
            }
        }
        for (const btnEl of new Set(btnEls)) {
            this.setInteractionsPerBufferTarget(btnEl, interaction.startResolvers.promise);
            if (!this.bufferedClicks.has(btnEl) && !this.bufferTargets.get(btnEl).handler) {
                const handler = (ev) => {
                    if (!this.shouldBuffer) {
                        return;
                    }
                    ev.preventDefault();
                    ev.stopImmediatePropagation();
                    const restore = addLoadingEffect(btnEl);
                    this.bufferedClicks.set(btnEl, { event: ev, restore });
                };
                btnEl.addEventListener("click", handler, { capture: true, once: true });
                this.bufferTargets.get(btnEl).handler = handler;
            }
        }
    }

    setInteractionsPerBufferTarget(el, interactionStartPromise) {
        if (!this.bufferTargets.has(el)) {
            this.bufferTargets.set(el, {
                interactionStarts: new Set([interactionStartPromise]),
                handler: undefined,
            });
        } else {
            this.bufferTargets.get(el).interactionStarts.add(interactionStartPromise);
        }
    }

    /**
     * Dispatches a click event on all buffered clicks targets.
     */
    retriggerBufferedClicks() {
        for (const [btnEl, { interactionStarts }] of this.bufferTargets.entries()) {
            const startProms = new Set(interactionStarts);
            for (const interaction of this.interactions) {
                if (interaction.el.contains(btnEl)) {
                    startProms.add(interaction.startResolvers.promise);
                }
            }
            Promise.allSettled(startProms).then(() => {
                if (!this.bufferedClicks.has(btnEl)) {
                    return;
                }
                const { event, restore } = this.bufferedClicks.get(btnEl);
                restore();
                if (isClickable(btnEl)) {
                    event.target.dispatchEvent(new event.constructor(event.type, event));
                }
                this.bufferedClicks.delete(btnEl);
            });
        }
    }

    /**
     * Removes elements from clicks to be retriggered.
     *
     * @param {HTMLElement} el - root stopped
     * @param {Object} interaction - Colibri instance
     */
    unbufferClicks(el, interaction) {
        for (const [btnEl, { interactionStarts, handler }] of this.bufferTargets.entries()) {
            if (el === btnEl || el.contains(btnEl)) {
                if (!interactionStarts.has(interaction.startResolvers.promise)) {
                    continue;
                }
                interactionStarts.delete(interaction.startResolvers.promise);
                interaction.startResolvers.promise.catch(() => {});
                interaction.startResolvers.reject();
                if (!interactionStarts.size) {
                    if (!this.bufferedClicks.get(btnEl)) {
                        btnEl.removeEventListener("click", handler, { capture: true, once: true });
                    } else {
                        this.bufferedClicks.get(btnEl).restore();
                        this.bufferedClicks.delete(btnEl);
                    }
                    this.bufferTargets.delete(btnEl);
                }
            }
        }
    }
}

export const publicInteractionService = {
    async start(env) {
        // fallback if #wrapwrap is not present in the dom
        const el = document.querySelector("#wrapwrap") || document.querySelector("body");
        const Interactions = registry.category("public.interactions").getAll();
        const service = new InteractionService(el, env);
        service.activate(Interactions);
        return service;
    },
};

registry.category("services").add("public.interactions", publicInteractionService);
