/**
 * This is a mini framework designed to make it easy to describe the dynamic
 * content of a "interaction".
 */

let owl = null;
let Markup = null;

export const INITIAL_VALUE = Symbol("initial value");
// Return this from event handlers to skip updateContent.
export const SKIP_IMPLICIT_UPDATE = Symbol();

export class Colibri {
    constructor(core, I, el) {
        this.el = el;
        this.isReady = false;
        this.hasStarted = false;
        this.isUpdating = false;
        this.isDestroyed = false;
        this.dynamicAttrs = [];
        this.tOuts = [];
        this.cleanups = [];
        this.listeners = new Map();
        this.dynamicNodes = new Map();
        this.core = core;
        this.interaction = new I(el, core.env, this);
        this.setupInteraction();
    }

    setupInteraction() {
        this.interaction.setup();
    }

    destroyInteraction() {
        for (const cleanup of this.cleanups.reverse()) {
            cleanup();
        }
        this.cleanups = [];
        this.interaction.destroy();
    }

    startInteraction(content) {
        if (content) {
            this.processContent(content);
            this.updateContent();
        }
        this.interaction.start();
        this.hasStarted = true;
    }

    async start() {
        await this.interaction.willStart();
        if (this.isDestroyed) {
            return;
        }
        this.isReady = true;
        const content = this.interaction.dynamicContent;
        this.startInteraction(content);
    }

    addListener(nodes, event, fn, options) {
        if (typeof fn !== "function") {
            throw new Error(`Invalid listener for event '${event}' (not a function)`);
        }
        if (!this.isReady) {
            throw new Error(
                "this.addListener can only be called after the interaction is started. Maybe move the call in the start method."
            );
        }
        const re = /^(?<event>.*)\.(?<suffix>prevent|stop|capture|once|noUpdate|withTarget)$/;
        let groups = re.exec(event)?.groups;
        while (groups) {
            fn = {
                prevent:
                    (f) =>
                    (ev, ...args) => {
                        ev.preventDefault();
                        return f.call(this.interaction, ev, ...args);
                    },
                stop:
                    (f) =>
                    (ev, ...args) => {
                        ev.stopPropagation();
                        return f.call(this.interaction, ev, ...args);
                    },
                capture: (f) => {
                    options ||= {};
                    options.capture = true;
                    return f;
                },
                once: (f) => {
                    options ||= {};
                    options.once = true;
                    return f;
                },
                noUpdate:
                    (f) =>
                    (...args) => {
                        f.call(this.interaction, ...args);
                        return SKIP_IMPLICIT_UPDATE;
                    },
                withTarget:
                    (f) =>
                    (ev, ...args) => {
                        const currentTarget = ev.currentTarget;
                        return f.call(this.interaction, ev, currentTarget, ...args);
                    },
            }[groups.suffix](fn);
            event = groups.event;
            groups = re.exec(event)?.groups;
        }
        const handler = fn.isHandler
            ? fn
            : async (...args) => {
                  if (SKIP_IMPLICIT_UPDATE !== (await fn.call(this.interaction, ...args))) {
                      if (!this.isDestroyed) {
                          this.updateContent();
                      }
                  }
              };
        handler.isHandler = true;
        for (const node of nodes) {
            node.addEventListener(event, handler, options);
            this.cleanups.push(() => node.removeEventListener(event, handler, options));
        }
        return [event, handler, options];
    }

    refreshNodes() {
        for (const sel of this.dynamicNodes.keys()) {
            const nodes = this.getNodes(sel);
            if (this.listeners.has(sel)) {
                const newNodes = new Set(nodes);
                const oldNodes = this.dynamicNodes.get(sel);
                const events = this.listeners.get(sel);
                const toRemove = new Set();
                for (const node of oldNodes) {
                    if (newNodes.has(node)) {
                        newNodes.delete(node);
                    } else {
                        toRemove.add(node);
                    }
                }
                for (const event of Object.keys(events)) {
                    const [handler, options] = events[event];
                    for (const node of toRemove) {
                        node.removeEventListener(event, handler, options);
                    }
                    if (newNodes.size) {
                        this.addListener(newNodes, event, handler, options);
                    }
                }
            }
            this.dynamicNodes.set(sel, nodes);
        }
    }

    mapSelectorToListeners(sel, event, handler, options) {
        if (this.listeners.has(sel)) {
            this.listeners.get(sel)[event] = [handler, options];
        } else {
            this.listeners.set(sel, { [event]: [handler, options] });
        }
    }

    mountComponent(node, C, props, position = "beforeend") {
        const root = this.core.prepareRoot(node, C, props, position);
        root.mount();
        this.cleanups.push(() => root.destroy());
        return root.destroy;
    }

    applyTOut(el, value, initialValue) {
        if (value === INITIAL_VALUE) {
            value = initialValue;
        }
        if (!Markup) {
            if (owl) {
                Markup = owl.markup("").constructor;
            }
        }
        if (Markup && value instanceof Markup) {
            let nodes = el === this.interaction.el ? el.children : [el];
            for (const node of nodes) {
                this.core.env.services["public.interactions"].stopInteractions(node);
            }
            el.innerHTML = value;
            if (el === this.interaction.el) {
                nodes = el.children;
            }
            for (const node of nodes) {
                this.core.env.services["public.interactions"].startInteractions(node);
            }
            this.refreshNodes();
        } else {
            el.textContent = value;
        }
    }

    applyAttr(el, attr, value, initialValue) {
        if (attr === "class") {
            if (typeof value !== "object") {
                throw new Error("t-att-class directive expects an object");
            }
            for (const cl in value) {
                let toApply = value[cl];
                for (const c of cl.trim().split(" ")) {
                    if (toApply === INITIAL_VALUE) {
                        toApply = initialValue[cl];
                    }
                    el.classList.toggle(c, toApply || false);
                }
            }
        } else if (attr === "style") {
            if (typeof value !== "object") {
                throw new Error("t-att-style directive expects an object");
            }
            for (const prop in value) {
                let style = value[prop];
                if (style === INITIAL_VALUE) {
                    style = initialValue[prop];
                }
                if (style === undefined) {
                    el.style.removeProperty(prop);
                } else {
                    style = String(style);
                    if (style.endsWith(" !important")) {
                        el.style.setProperty(
                            prop,
                            style.substring(0, style.length - 11),
                            "important"
                        );
                    } else {
                        el.style.setProperty(prop, style);
                    }
                }
            }
        } else {
            if (value === INITIAL_VALUE) {
                value = initialValue;
            }
            if ([false, undefined, null].includes(value)) {
                el.removeAttribute(attr);
            } else {
                if (value === true) {
                    value = attr;
                }
                el.setAttribute(attr, value);
            }
        }
    }

    getNodes(sel) {
        const selectors = this.interaction.dynamicSelectors;
        if (sel in selectors) {
            const elems = selectors[sel]();
            if (elems) {
                if (elems.nodeName && ["FORM", "SELECT"].includes(elems.nodeName)) {
                    return [elems];
                }
                return elems[Symbol.iterator] ? elems : [elems];
            } else {
                return [];
            }
        }
        return this.interaction.el.querySelectorAll(sel);
    }

    processContent(content) {
        for (const sel in content) {
            if (sel.startsWith("t-")) {
                throw new Error(
                    `Selector missing for key ${sel} in dynamicContent (interaction '${this.interaction.constructor.name}').`
                );
            }
            let nodes;
            if (this.dynamicNodes.has(sel)) {
                nodes = this.dynamicNodes.get(sel);
            } else {
                nodes = this.getNodes(sel);
                this.dynamicNodes.set(sel, nodes);
            }
            const descr = content[sel];
            for (const directive in descr) {
                const value = descr[directive];
                if (directive.startsWith("t-on-")) {
                    const ev = directive.slice(5);
                    const [event, handler, options] = this.addListener(nodes, ev, value);
                    this.mapSelectorToListeners(sel, event, handler, options);
                } else if (directive.startsWith("t-att-")) {
                    const attr = directive.slice(6);
                    this.dynamicAttrs.push({
                        sel,
                        attr,
                        definition: value,
                        initialValues: null,
                    });
                } else if (directive === "t-out") {
                    this.tOuts.push({ sel, definition: value, initialValue: null });
                } else if (directive === "t-component") {
                    const { Component } = odoo.loader.modules.get("@odoo/owl");
                    if (Object.prototype.isPrototypeOf.call(Component, value)) {
                        for (const node of nodes) {
                            this.mountComponent(node, value);
                        }
                    } else {
                        for (const node of nodes) {
                            this.mountComponent(node, ...value(node));
                        }
                    }
                } else {
                    const suffix = directive.startsWith("t-") ? "" : " (should start with t-)";
                    throw new Error(`Invalid directive: '${directive}'${suffix}`);
                }
            }
        }
    }

    updateContent() {
        if (this.isDestroyed || !this.isReady) {
            throw new Error(
                "Cannot update content of an interaction that is not ready or is destroyed"
            );
        }
        if (this.isUpdating) {
            throw new Error("Updatecontent should not be called while interaction is updating");
        }
        this.isUpdating = true;
        if (this.hasStarted) {
            this.refreshNodes();
        }
        const errors = [];
        const interaction = this.interaction;
        for (const dynamicAttr of this.dynamicAttrs) {
            let { sel, attr, definition, initialValues } = dynamicAttr;
            const nodes = this.dynamicNodes.get(sel) || [];
            if (!initialValues && nodes.length) {
                initialValues = new Map();
                dynamicAttr.initialValues = initialValues;
            }
            for (const node of nodes) {
                try {
                    const value = definition.call(interaction, node);
                    if (!initialValues || !initialValues.has(node)) {
                        let attrValue;
                        switch (attr) {
                            case "class":
                                attrValue = {};
                                for (const classNames of Object.keys(value)) {
                                    attrValue[classNames] = node.classList.contains(classNames);
                                }
                                break;
                            case "style":
                                attrValue = {};
                                for (const property of Object.keys(value)) {
                                    const propertyValue = node.style.getPropertyValue(property);
                                    const priority = node.style.getPropertyPriority(property);
                                    attrValue[property] = propertyValue
                                        ? propertyValue + (priority ? ` !${priority}` : "")
                                        : undefined;
                                }
                                break;
                            default:
                                attrValue = node.getAttribute(attr);
                        }
                        initialValues.set(node, attrValue);
                    }
                    this.applyAttr(node, attr, value, dynamicAttr.initialValues.get(node));
                } catch (e) {
                    errors.push({ error: e, attribute: attr });
                }
            }
        }
        for (const tOut of this.tOuts) {
            let { sel, definition, initialValue } = tOut;
            const nodes = this.dynamicNodes.get(sel) || [];
            if (!initialValue && nodes.length) {
                initialValue = new Map();
                tOut.initialValue = initialValue;
            }
            for (const node of nodes) {
                if (!initialValue || !initialValue.has(node)) {
                    if (!owl) {
                        owl = odoo.loader.modules.get("@odoo/owl");
                    }
                    const value = node.children.length
                        ? owl.markup(node.innerHTML)
                        : node.textContent;
                    initialValue.set(node, value);
                }
                this.applyTOut(
                    node,
                    definition.call(interaction, node),
                    tOut.initialValue.get(node)
                );
            }
        }
        this.isUpdating = false;
        if (errors.length) {
            const { attribute, error } = errors[0];
            throw Error(
                `An error occured while updating dynamic attribute '${attribute}' (in interaction '${this.interaction.constructor.name}')`,
                { cause: error }
            );
        }
    }

    destroy() {
        // restore t-att to their initial values
        for (const dynAttrs of this.dynamicAttrs) {
            const { sel, attr, initialValues } = dynAttrs;
            if (!initialValues) {
                continue;
            }
            for (const node of this.dynamicNodes.get(sel) || []) {
                if (initialValues.has(node)) {
                    const initialValue = initialValues.get(node);
                    this.applyAttr(node, attr, initialValue);
                }
            }
        }

        this.listeners.clear();
        this.dynamicNodes.clear();
        this.destroyInteraction();
        this.core = null;
        this.isDestroyed = true;
        this.isReady = false;
    }

    /**
     * Patchable mechanism to handle context-specific protection of a specific
     * chunk of synchronous code after returning from an asynchronous one.
     * This should typically be used around code that follows an
     * await waitFor(...).
     */
    protectSyncAfterAsync(interaction, name, fn) {
        return fn.bind(interaction);
    }
}
