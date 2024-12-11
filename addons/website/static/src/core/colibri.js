/**
 * This is a mini framework designed to make it easy to describe the dynamic
 * content of a "interaction".
 */

let owl = null;
let Markup = null;

// Return this from event handlers to skip updateContent.
export const SKIP_IMPLICIT_UPDATE = Symbol();

export class Colibri {
    constructor(core, I, el) {
        this.el = el;
        this.isReady = false;
        this.isUpdating = false;
        this.isDestroyed = false;
        this.dynamicAttrs = [];
        this.tOuts = [];
        this.cleanups = [];
        this.core = core;
        this.interaction = new I(el, core.env, this);
        if (I.dynamicContent) {
            throw new Error(`The dynamic content object should be defined on the instance, not on the class (${I.name})`);
        }
        this.interaction.setup();
    }
    async start() {
        await this.interaction.willStart();
        if (this.isDestroyed) {
            return;
        }
        this.isReady = true;
        const content = this.interaction.dynamicContent;
        if (content) {
            this.processContent(content);
            this.updateContent();
        }
        this.interaction.start();
    }

    addListener(nodes, event, fn, options) {
        if (!fn) {
            throw new Error(`Invalid listener for event '${event}' (received falsy value)`);
        }
        if (!this.isReady) {
            throw new Error("this.addListener can only be called after the interaction is started. Maybe move the call in the start method.");
        }
        const re = /^(?<event>.*)\.(?<suffix>prevent|stop|capture|noupdate)$/;
        let groups = re.exec(event)?.groups;
        while (groups) {
            fn = {
                prevent: (f) => ((ev) => {
                    ev.preventDefault();
                    return f(ev);
                }),
                stop: (f) => ((ev) => {
                    ev.stopPropagation();
                    return f(ev);
                }),
                capture: (f) => {
                    options ||= {};
                    options.capture = true;
                    return f;
                },
                noupdate: (f) => ((ev) => {
                    f(ev);
                    return SKIP_IMPLICIT_UPDATE;
                }),
            }[groups.suffix](fn);
            event = groups.event;
            groups = re.exec(event)?.groups;
        }
        const handler = (ev) => {
            if (SKIP_IMPLICIT_UPDATE !== fn.call(this.interaction, ev)) {
                this.updateContent();
            }
        };
        const removeListeners = [];
        for (const node of nodes) {
            node.addEventListener(event, handler, options);
            const removeListener = () => node.removeEventListener(event, handler, options);
            this.cleanups.push(removeListener);
            removeListeners.push(removeListener);
        }
        return removeListeners;
    }

    mountComponent(nodes, C, props) {
        for (let node of nodes) {
            const root = this.core.prepareRoot(node, C, props);
            root.mount();
            this.cleanups.push(() => root.destroy());
        }
    }

    applyTOut(el, value) {
        if (!Markup) {
            owl = odoo.loader.modules.get("@odoo/owl");
            if (owl) {
                Markup = owl.markup("").constructor;
            }
        }
        if (Markup && value instanceof Markup) {
            el.innerHTML = value;
        } else {
            el.textContent = value;
        }
    }

    applyAttr(el, attr, value) {
        if (attr === "class") {
            if (typeof value !== "object") {
                throw new Error("t-att-class directive expects an object");
            }
            for (const cl in value) {
                for (const c of cl.trim().split(" ")) {
                    el.classList.toggle(c, value[cl] || false);
                }
            }
        } else if (attr === "style") {
            if (typeof value !== "object") {
                throw new Error("t-att-style directive expects an object");
            }
            for (const prop in value) {
                let style = value[prop];
                if (style === undefined) {
                    el.style.removeProperty(prop);
                } else {
                    style = String(style);
                    if (style.endsWith(" !important")) {
                        el.style.setProperty(prop, style.substring(0, style.length - 11), "important");
                    } else {
                        el.style.setProperty(prop, style);
                    }
                }
            }
        } else {
            if (value) {
                el.setAttribute(attr, value);
            } else {
                el.removeAttribute(attr);
            }
        }
    }

    processContent(content) {
        const interaction = this.interaction;

        const el = interaction.el;
        const nodes = {};
        const selectors = interaction.dynamicSelectors;


        const getNodes = (sel) => {
            if (sel in selectors) {
                const elem = selectors[sel]();
                return elem ? [elem] : [];
            }
            if (!(sel in nodes)) {
                nodes[sel] = el.querySelectorAll(sel);
            }
            return nodes[sel];
        };

        for (const [sel, directive, value] of generateEntries(content)) {
            const nodes = getNodes(sel);
            if (directive.startsWith("t-on-")) {
                const ev = directive.slice(5);
                this.addListener(nodes, ev, value);
            } else if (directive.startsWith("t-att-")) {
                const attr = directive.slice(6);
                this.dynamicAttrs.push({nodes, attr, definition: value, initialValues: null});
            } else if (directive === "t-out") {
                this.tOuts.push([nodes, value]);
            } else if (directive === "t-component") {
                const { Component } = odoo.loader.modules.get("@odoo/owl");
                if (Component.isPrototypeOf(value)) {
                    this.mountComponent(nodes, value);
                } else {
                    this.mountComponent(nodes, ...value());
                }
            } else {
                const suffix = directive.startsWith("t-")
                    ? ""
                    : " (should start with t-)";
                throw new Error(`Invalid directive: '${directive}'${suffix}`);
            }
        }

    }

    updateContent() {
        if (this.isDestroyed || !this.isReady) {
            throw new Error("Cannot update content of an interaction that is not ready or is destroyed");
        }
        if (this.isUpdating) {
            throw new Error("Updatecontent should not be called while interaction is updating");
        }
        this.isUpdating = true;
        const errors = [];
        const interaction = this.interaction;
        for (const dynamicAttr of this.dynamicAttrs) {
            const {nodes, attr, definition, initialValues} = dynamicAttr;
            let valuePerNode;
            if (!initialValues) {
                valuePerNode = new Map();
                dynamicAttr.initialValues = valuePerNode;
            }
            for (const node of nodes) {
                try {
                    const value = definition.call(interaction, node);
                    if (!initialValues) {
                        let attrValue;
                        switch (attr) {
                            case "class":
                                attrValue = [];
                                for (const classNames of Object.keys(value)) {
                                    attrValue[classNames] = node.classList.contains(classNames);
                                }
                                break;
                            case "style":
                                attrValue = {};
                                for (const property of Object.keys(value)) {
                                    const propertyValue = node.style.getPropertyValue(property);
                                    const priority = node.style.getPropertyPriority(property);
                                    attrValue[property] = propertyValue ? (propertyValue + (priority ? ` !${priority}` : "")) : "";
                                }
                                break;
                            default:
                                attrValue = node.getAttribute(attr);
                        }
                        valuePerNode.set(node, attrValue);
                    }
                    this.applyAttr(node, attr, value);
                } catch (e) {
                    errors.push({ error: e, attribute: attr });
                }
            }
        }
        for (const [nodes, definition] of this.tOuts) {
            for (const node of nodes) {
                this.applyTOut(node, definition.call(interaction, node));
            }
        }
        this.isUpdating = false;
        if (errors.length) {
            const { attribute, error } = errors[0];
            throw Error(`An error occured while updating dynamic attribute '${attribute}' (in interaction '${this.interaction.constructor.name}')`, { cause: error });
        }

    }

    destroy() {
        // restore t-att to their initial values
        for (const dynAttrs of this.dynamicAttrs) {
            const {nodes, attr, definition, initialValues} = dynAttrs;
            if (!initialValues) {
                continue;
            }
            for (const node of nodes) {
                const initialValue = initialValues.get(node);
                this.applyAttr(node, attr, initialValue);
            }
        }

        for (const cleanup of this.cleanups.reverse()) {
            cleanup();
        }
        this.cleanups = [];
        this.interaction.destroy();
        this.core = null;
        this.isDestroyed = true;
        this.isReady = false;
    }
}

function* generateEntries(content) {
    for (const key in content) {
        const value = content[key];
        if (typeof value === "object") {
            for (const directive in value) {
                yield [key, directive, value[directive]];
            }
        } else {
            const lastColon = key.lastIndexOf(":");
            const selector = key.slice(0, lastColon);
            const directive = key.slice(lastColon + 1);
            yield [selector, directive, value];
        }
    }
}
