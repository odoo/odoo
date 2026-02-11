// @ts-ignore
const owl = globalThis.owl;

/**
 * @type {any}
 */
let currentNode = null;

class Component extends owl.Component {
    static template = "";

    /**
     * @param {any} props
     * @param {any} env
     * @param {any} node
     */
    constructor(props, env, node) {
        super(props, env, node);
        this.props = props;
        this.env = env;
        this.__owl__ = node;
        currentNode = node;
    }

    setup() {}

    /**
     * @param {boolean} deep
     */
    render(deep = false) {
        this.__owl__.render(deep === true);
    }
};
owl.Component = Component;

function getCurrentNode() {
    if (!currentNode) {
        throw new Error("No current node");
    }
    return currentNode;
}

/**
 * @param {any} component
 * @param {boolean} [deep]
 */
export function render(component, deep = false) {
    component.__owl__.render(deep);
}

/**
 * @param {() => void} cb
 */
export function onWillRender(cb) {
    const node = getCurrentNode();
    const renderFn = node.renderFn;
    node.renderFn = () => {
        cb.call(node.component);
        return renderFn();
    };
}

/**
 * @param {() => void} cb
 */
export function onRendered(cb) {
    const node = getCurrentNode();
    const renderFn = node.renderFn;
    node.renderFn = () => {
        const result = renderFn();
        cb.call(node.component);
        return result;
    };
}

/**
 * @param {string} name
 */
export function useRef(name) {
    return owl.useRef(name);
}

/**
 */
export function useComponent() {
    return getCurrentNode().component;
}

/**
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
 * @template T
 * @param {T} data
 */
export function useState(data) {
    return owl.useState(data);
}

/**
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
 * @param {Function} effect
 * @param {() => any[]} computeDependencies
 */
export function useLayoutEffect(effect, computeDependencies = () => [NaN]) {
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

export function useEnv() {
    return owl.useEnv();
}

/**
 * @param {object} extension
 */
export function useSubEnv(extension) {
    return owl.useSubEnv(extension);
}

/**
 * @param {object} extension
 */
export function useChildSubEnv(extension) {
    return owl.useChildSubEnv(extension);
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

const customDirectives = {
    /**
     * @param {HTMLElement} node
     * @param {string} value
     */
    ref: (node, value) => {
        node.setAttribute("t-ref", value);
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
        node.setAttribute(attribute, value);
    },
    /**
     * @param {HTMLElement} node
     * @param {string} value
     */
    portal: (node, value) => {
        if (node.nodeName.toLowerCase() !== "t") {
            throw new Error("t-custom-portal should be on a 't' element");
        }
        node.setAttribute("t-portal", value);
    },
};

const globalValues = {
    Portal,
};

class App extends owl.App {
    /**
     * @param {any} component
     * @param {any} config
     */
    constructor(component, config) {
        super(component, {
            ...config,
            customDirectives: {
                ...customDirectives,
                ...config.customDirectives,
            },
            globalValues: {
                ...globalValues,
                ...config.globalValues,
            },
        });
    }
}
owl.App = App;
