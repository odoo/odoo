/**
 * Owl 2 → Owl 3 compatibility layer.
 *
 * This file patches Owl 3 so that existing Owl 2 code can continue to run
 * with minimal changes. It is intended as a temporary bridge to ease
 * incremental migration from Owl 2 to Owl 3.
 *
 * ---------------------------------------------------------------------------
 * Setup (required to run Owl 2 code on Owl 3)
 * ---------------------------------------------------------------------------
 *
 * 1. Update template directives:
 *    - replace `t-portal` → `t-custom-portal`
 *    - replace `t-ref`    → `t-custom-ref`
 *    - replace `t-model`  → `t-custom-model`
 *
 * 2. Load this file immediately after Owl 3.
 *
 * 3. Update hooks:
 *    - replace all `useEffect` with `useLayoutEffect`
 *      import { useLayoutEffect } from "@odoo/owl";
 *
 * ---------------------------------------------------------------------------
 * Migration (once the app builds successfully)
 * ---------------------------------------------------------------------------
 *
 * Gradually remove the compatibility layer by migrating to native Owl 3:
 *
 * - replace `t-custom-portal` with proper Owl 3 portal usage
 * - replace `t-custom-ref` with `t-ref` + signals
 * - replace `t-custom-model` with `t-model` + signals
 * - convert `useLayoutEffect` back to `useEffect` where appropriate
 *
 * The end goal is to eliminate all compatibility shims.
 */

// @ts-ignore
const owl = globalThis.owl;

class Component extends owl.Component {
    static template = "";
    static props = {};
    static defaultProps = {};

    /**
     * @param {any} node
     */
    constructor(node) {
        super(node);
        this.props = owl.props(null, this.constructor.defaultProps);
        this.env = useChildEnv();
        this.__owl__ = node;
    }

    setup() {}

    /**
     * @param {boolean} deep
     */
    render(deep = false) {
        this.__owl__.render(deep === true);
    }
}
owl.Component = Component;

/**
 * @param {() => void} cb
 */
owl.onWillRender = function onWillRender(cb) {
    const node = owl.useScope();
    const renderFn = node.renderFn;
    node.renderFn = () => {
        cb.call(node.component);
        return renderFn();
    };
};

/**
 * @param {() => void} cb
 */
owl.onRendered = function onRendered(cb) {
    const node = owl.useScope();
    const renderFn = node.renderFn;
    node.renderFn = () => {
        const result = renderFn();
        cb.call(node.component);
        return result;
    };
};

/**
 * @param {string} name
 */
owl.useRef = function useRef(name) {
    const node = owl.useScope();
    if (!node.__refs__) {
        node.__refs__ = {};
    }
    if (!node.__refs__[name]) {
        node.__refs__[name] = owl.signal(null);
    }
    return {
        get el() {
            const signal = node.__refs__[name];
            // untrack all the time to do what owl2 did
            // while having an actual signal under the hood
            // fully recognizable by owl3
            return owl.untrack(signal);
        },
    };
};

/**
 */
owl.useComponent = function useComponent() {
    return owl.useScope().component;
};

/**
 * @param {HTMLElement} target
 * @param {string} eventName
 * @param {Function} handler
 * @param {any} eventParams
 */
owl.useExternalListener = function useExternalListener(target, eventName, handler, eventParams) {
    const node = owl.useScope();
    const boundHandler = handler.bind(node.component);
    owl.onMounted(() => target.addEventListener(eventName, boundHandler, eventParams));
    owl.onWillUnmount(() => target.removeEventListener(eventName, boundHandler, eventParams));
};

/**
 * @param {Function} effect
 * @param {() => any[]} computeDependencies
 */
owl.useLayoutEffect = function useLayoutEffect(effect, computeDependencies = () => [NaN]) {
    // /** @type {Function} */
    // let cleanup;
    // /** @type {any[]} */
    // let dependencies;
    // owl.onWillRender(() => {
    //     try {
    //         computeDependencies();
    //     } catch {
    //         // just need to read dependencies to subscribe to signals
    //     }
    // });
    // owl.onMounted(() => {
    //     dependencies = computeDependencies();
    //     cleanup = effect(...dependencies);
    // });
    // owl.onPatched(() => {
    //     const newDeps = computeDependencies();
    //     const shouldReapply = newDeps.some((val, i) => val !== dependencies[i]);
    //     if (shouldReapply) {
    //         dependencies = newDeps;
    //         if (cleanup) {
    //             cleanup();
    //         }
    //         cleanup = effect(...dependencies);
    //     }
    // });
    // owl.onWillUnmount(() => cleanup && cleanup());
};

class EnvPlugin extends owl.Plugin {
    static id = "__ENV__";
    env = owl.config("env") ?? {};
}

owl.useEnv = function useEnv() {
    return owl.useScope().component.env;
};

function useChildEnv() {
    return owl.plugin(EnvPlugin).env;
}
owl.useChildEnv = useChildEnv;

/**
 * @param {object} env
 */
function provideEnv(env) {
    owl.providePlugins([EnvPlugin], { env });
    return env;
}
owl.provideEnv = provideEnv;

/**
 * @param {object} extension
 */
function extendEnv(extension) {
    const env = Object.create(useChildEnv());
    const descrs = Object.getOwnPropertyDescriptors(extension);
    const subEnv = Object.freeze(Object.defineProperties(env, descrs));
    return provideEnv(subEnv);
}

/**
 * @param {object} extension
 */
owl.useSubEnv = function useSubEnv(extension) {
    const component = owl.useScope().component;
    component.env = extendEnv(extension);
};

/**
 * @param {object} extension
 */
owl.useChildSubEnv = function useChildSubEnv(extension) {
    extendEnv(extension);
};

class VPortal extends owl.blockDom.text("").constructor {
    /**
     * @param {any} selector
     * @param {any} content
     */
    constructor(selector, content) {
        super("");
        this.content = content;
        this.selector = selector;
        this.target = null;
    }

    /**
     * @param {any} parent
     * @param {any} anchor
     */
    mount(parent, anchor) {
        super.mount(parent, anchor);
        this.target = document.querySelector(this.selector);
        if (this.target) {
            this.content.mount(this.target, null);
        } else {
            this.content.mount(parent, anchor);
        }
    }

    beforeRemove() {
        this.content.beforeRemove();
    }

    remove() {
        if (this.content) {
            super.remove();
            this.content.remove();
            this.content = null;
        }
    }

    /**
     * @param {any} other
     */
    patch(other) {
        super.patch(other);
        if (this.content) {
            this.content.patch(other.content, true);
        } else {
            this.content = other.content;
            this.content.mount(this.target, null);
        }
    }
}

class Portal extends owl.Component {
    static template = owl.xml`<t t-call-slot="default"/>`;
    static props = { selector: String, slots: true };

    setup() {
        const node = this.__owl__;
        const renderContent = node.renderFn;
        node.renderFn = (/** @type {any[]} */ ...args) =>
            new VPortal(node.props.selector, renderContent(...args));

        owl.onMounted(() => {
            const portal = node.bdom;
            if (!portal.target) {
                const target = portal.el.ownerDocument.querySelector(node.props.selector);
                if (target) {
                    portal.content.moveBeforeDOMNode(target.firstChild, target);
                } else {
                    throw new Error("invalid portal target");
                }
            }
        });

        owl.onWillUnmount(() => {
            const portal = node.bdom;
            portal.remove();
        });
    }
}

let refId = 0;
const customDirectives = {
    /**
     * @param {HTMLElement} node
     * @param {string} value
     */
    ref: (node, value) => {
        const refName = `"` + value.replaceAll(/\{\{(.+?)\}\}/g, `" + $1 + "`) + `"`;
        node.setAttribute("t-ref", `__globals__.createRefSignal(this, ${refName}, ${++refId})`);
    },
    /**
     * @param {HTMLElement} node
     * @param {string} value
     * @param {string[]} modifiers
     */
    model: (node, value, modifiers) => {
        let attribute = "t-model";
        for (const modifier of modifiers) {
            attribute += `.${modifier}`;
        }
        const getter = `() => ${value}`;
        const setter = `(nv) => {${value} = nv;}`;
        node.setAttribute(attribute, `__globals__.createModelSignal(${getter}, ${setter})`);
    },
    /**
     * @param {HTMLElement} node
     * @param {string} value
     */
    portal: (node, value) => {
        if (node.nodeName.toLowerCase() !== "t") {
            throw new Error("t-custom-portal should be on a 't' element");
        }
        node.setAttribute("t-component", "__globals__.Portal");
        node.setAttribute("selector", value);
    },
};

const globalValues = {
    /**
     * @param {any} component
     * @param {string} refName
     */
    createRefSignal: (component, refName, refId) => {
        const node = component.__owl__;
        if (!node.__refs__) {
            node.__refs__ = {};
        }
        if (!node.__refs__[refName]) {
            node.__refs__[refName] = owl.signal(null);
        }
        return node.__refs__[refName];
    },
    /**
     * @param {Function} getter
     * @param {Function} setter
     */
    createModelSignal: (getter, setter) => Object.assign(getter, { set: setter }),
    Portal,
};

class App extends owl.App {
    /**
     * @param {any} config
     */
    constructor(config) {
        super({
            ...config,
            customDirectives: {
                ...customDirectives,
                ...config.customDirectives,
            },
            globalValues: {
                ...globalValues,
                ...config.globalValues,
            },
            config: config.config
                ? Object.assign(Object.create(config.config), {
                      env: config.env,
                  })
                : { env: config.env },
        });
        this.pluginManager.startPlugins([EnvPlugin]);
        this.env = config.env ?? {};
    }

    createRoot(component, config = {}) {
        if (config.env) {
            component = {
                [component.name]: class extends component {
                    constructor(node) {
                        provideEnv(config.env);
                        super(node);
                    }
                },
            }[component.name];
        }
        return super.createRoot(component, config);
    }
}
owl.App = App;

/**
 * @param {any} C
 * @param {any} target
 * @param {any} config
 */
async function mount(C, target, config = {}) {
    return new App(config).createRoot(C, config).mount(target, config);
}
owl.mount = mount;

owl.__ODOO_COMPATIBILITY_LAYER_ADDED__ = true;
