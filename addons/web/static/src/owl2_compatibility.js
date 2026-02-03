/*

This file contains the following deprecated features:
- onRendered
- onWillRender
- reactive
- this.env
- this.props
- this.render
- useComponent
- useEffect
- useExternalListener
- useRef
- useState

It also defines old implementation of t-ref, t-model and t-portal.

*/

// @ts-ignore
const owl = globalThis.owl;

/**
 * @type {any}
 */
let currentNode = null;

owl.Component = class Component extends owl.Component {
    static template = "";

    /**
     * @param {any} node
     */
    constructor(node) {
        super(node);
        this.__owl__ = node;
        this.__refs__ = {};
        this.props = new Proxy(
            {},
            {
                get(_, p) {
                    return node.props[p];
                },
            }
        );
        const envPlugin =
            this.__owl__.pluginManager.get(EnvPlugin) ||
            this.__owl__.pluginManager.startPlugin(EnvPlugin);
        this.env = envPlugin;
        currentNode = node;
    }

    setup() {}
};

function getCurrentNode() {
    if (!currentNode) {
        throw new Error("No current node");
    }
    return currentNode;
}

/**
 * @deprecated
 * @param {any} component
 * @param {boolean} [deep]
 */
export function render(component, deep = false) {
    component.__owl__.render(deep);
}

/**
 * @deprecated
 * @param {() => void} cb
 */
export function onWillRender(cb) {
    const node = getCurrentNode();
    const renderFn = node.renderFn;
    node.renderFn = () => {
        cb();
        return renderFn();
    };
}

/**
 * @deprecated
 * @param {() => void} cb
 */
export function onRendered(cb) {
    const node = getCurrentNode();
    const renderFn = node.renderFn;
    node.renderFn = () => {
        const result = renderFn();
        cb();
        return result;
    };
}

/**
 * @deprecated
 * @param {string} name
 * @returns {{ readonly el: HTMLElement | null }}
 */
export function useRef(name) {
    const component = getCurrentNode().component;
    return {
        get el() {
            return component.__refs__[name] || null;
        },
    };
}

/**
 * @deprecated
 */
export function useComponent() {
    return getCurrentNode().component;
}

/**
 * @deprecated
 * @param {HTMLElement} target
 * @param {string} eventName
 * @param {Function} handler
 * @param {any} eventParams
 */
export function useExternalListener(target, eventName, handler, eventParams) {
    const node = getCurrentNode();
    const boundHandler = handler.bind(node.component);
    owl.onMounted(() => target.addEventListener(eventName, boundHandler, eventParams));
    owl.onWillUnmount(() => target.removeEventListener(eventName, boundHandler, eventParams));
}

/**
 * @deprecated
 * @template T
 * @param {T} data
 */
export function useState(data) {
    return owl.useState(data);
}

/**
 * @deprecated
 * @template T
 * @param {T} data
 * @param {() => void} [callback]
 */
export function reactive(data, callback) {
    if (callback) {
        console.trace("reactive called with callback");
    }
    return owl.reactive(data, callback);
}

/**
 * @deprecated
 * @param {Function} effect
 * @param {() => any[]} computeDependencies
 */
export function useEffect(effect, computeDependencies = () => [NaN]) {
    /** @type {Function} */
    let cleanup;
    /** @type {any[]} */
    let dependencies;
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
}

class EnvPlugin extends owl.Plugin {
    static id = "EnvPlugin";
    env = {};
}

export function useEnv() {
    return getCurrentNode().component.env;
}

/**
 * @param {object} env
 * @param {object} extension
 */
function extendEnv(env, extension) {
    const subEnv = Object.assign(Object.create(env), extension);
    class SubEnvPlugin extends owl.Plugin {
        static id = "EnvPlugin";
        env = subEnv;
    }
    owl.providePlugins([SubEnvPlugin]);
    return subEnv;
}

/**
 * @param {object} extension
 */
export function useSubEnv(extension) {
    const component = getCurrentNode().component;
    component.env = extendEnv(component.env, extension);
}

/**
 * @param {object} extension
 */
export function useChildSubEnv(extension) {
    const component = getCurrentNode().component;
    extendEnv(component.env, extension);
}

class Portal extends owl.Component {
    static template = owl.xml`<t t-slot="default"/>`;

    setup() {
        const node = this.__owl__;

        owl.onMounted(() => {
            const portal = node.bdom;
            const target = document.querySelector(this.props.target);
            if (target) {
                portal.moveBeforeDOMNode(target.firstChild, target);
            } else {
                throw new Error("invalid portal target");
            }
        });

        owl.onWillUnmount(() => {
            const portal = node.bdom;
            portal.remove();
        });
    }
}

export const compatibilityDirectives = {
    /**
     * @param {HTMLElement} node
     * @param {string} value
     */
    ref: (node, value) => {
        const refName = value.startsWith("{{") ? value.slice(2, -2).trim() : `'${value}'`;
        node.setAttribute("t-ref", `__globals__.createRefSignal(this, ${refName})`);
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
        node.setAttribute("target", value);
    },
};

export const compatibilityGlobals = {
    /**
     * @param {any} component
     * @param {string} refName
     */
    createRefSignal: (component, refName) => ({
        /** @param {HTMLElement | null} value */
        set(value) {
            component.__refs__[refName] = value;
        },
    }),
    /**
     * @param {Function} getter
     * @param {Function} setter
     */
    createModelSignal: (getter, setter) => Object.assign(getter, { set: setter }),
    Portal,
};
