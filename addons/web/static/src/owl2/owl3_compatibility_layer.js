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
 * - replace `t-custom-model` with `t-model` + signals
 * - convert `useLayoutEffect` back to `useEffect` where appropriate
 *
 * The end goal is to eliminate all compatibility shims.
 */

// @ts-ignore
const owl = globalThis.owl;

class Component extends owl.Component {
    /**
     * @param {any} node
     */
    constructor(node) {
        super(node);
        if (this.constructor.props || this.constructor.defaultProps) {
            throw new Error(
                `Component "${this.constructor.name}" defines a static "props" or "defaultProps", ` +
                    `which Owl 3 ignores. Declare the props schema through "useProps" instead, ` +
                    `e.g. "props = useProps({ someProp: t.string().optional(defaultValue) })".`
            );
        }
        this.env = useEnv();
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

/** kept for spreadsheet */
owl.useComponent = function useComponent() {
    return owl.useScope().component;
};

/**
 * @param {Function} effect
 * @param {() => any[]} computeDependencies
 */
owl.useLayoutEffect = function useLayoutEffect(effect, computeDependencies = () => [NaN]) {
    /** @type {Function} */
    let cleanup;
    /** @type {any[]} */
    let dependencies;
    owl.onWillRender(() => {
        try {
            computeDependencies();
        } catch {
            // just need to read dependencies to subscribe to signals
        }
    });
    owl.onMounted(() => {
        dependencies = computeDependencies();
        cleanup = effect(...dependencies);
    });
    owl.onPatched(() => {
        const newDeps = computeDependencies();
        const shouldReapply = newDeps.some((val, i) => val !== dependencies[i]);
        if (shouldReapply) {
            dependencies = newDeps;
            if (cleanup) {
                cleanup();
            }
            cleanup = effect(...dependencies);
        }
    });
    owl.onWillUnmount(() => cleanup && cleanup());
};

class EnvPlugin extends owl.Plugin {
    static id = "__ENV__";
    static sequence = 0;
    env = owl.useConfig("env");
}

function useEnv() {
    return owl.usePlugin(EnvPlugin).env;
}
owl.useEnv = useEnv;

/**
 * @param {object} extension
 */
function useSubEnv(extension) {
    const env = Object.create(useEnv());
    const descrs = Object.getOwnPropertyDescriptors(extension);
    const subEnv = Object.freeze(Object.defineProperties(env, descrs));
    owl.providePlugins([EnvPlugin], { env: subEnv });

    const component = owl.useScope().component;
    component.env = subEnv;
}
owl.useSubEnv = useSubEnv;

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

/**
 * @param {HTMLElement} node
 * @param {string} value
 */
function portalDirective(node, value) {
    if (node.nodeName.toLowerCase() !== "t") {
        throw new Error("t-custom-portal should be on a 't' element");
    }
    node.setAttribute("t-component", "__globals__.Portal");
    node.setAttribute("selector", value);
}

class App extends owl.App {
    /**
     * @param {any} config
     */
    constructor(config) {
        config = {
            plugins: [],
            config: {},
            customDirectives: {},
            globalValues: {},
            ...config,
        };

        config.config.env ??= {};

        if (config.plugins instanceof owl.Resource) {
            config.plugins.add(EnvPlugin);
        } else {
            config.plugins.push(EnvPlugin);
        }

        config.customDirectives.portal ??= portalDirective;
        config.globalValues.Portal ??= Portal;

        super(config);
        this.env = config.config.env;
    }

    createRoot(component, config = {}) {
        if (config.env) {
            component = {
                [component.name]: class extends component {
                    constructor(node) {
                        owl.providePlugins([EnvPlugin], { env: config.env });
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
