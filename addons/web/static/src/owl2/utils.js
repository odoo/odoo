// @ts-ignore
const owl = globalThis.owl;

/**
 * @type {any}
 */
let currentNode = null;

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
        currentNode = node;
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
 * @param {any} value
 * @param {any} descr
 */
export function validate(value, descr) {
    // return owl.validate(...arguments);
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
    const node = getCurrentNode();
    if (!node.__refs__) {
        node.__refs__ = {};
    }
    return {
        get el() {
            return node.__refs__[name] || null;
        },
    };
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
    return owl.proxy(data);
}

/**
 * @template T
 * @param {T} data
 * @param {() => void} [callback]
 */
export function reactive(data, callback) {
    // if (callback) {
    //     console.trace("reactive called with callback");
    // }
    return owl.proxy(data);
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

class EnvPlugin extends owl.Plugin {
    static id = "__ENV__";
    env = owl.config("env") ?? {};
}

export function useEnv() {
    return getCurrentNode().component.env;
}

export function useChildEnv() {
    return owl.plugin(EnvPlugin).env;
}

/**
 * @param {object} env
 */
export function provideEnv(env) {
    owl.providePlugins([EnvPlugin], { env });
    return env;
}

/**
 * @param {object} extension
 */
function extendEnv(extension) {
    const env = useChildEnv();
    const subEnv = Object.assign(Object.create(env), extension);
    return provideEnv(subEnv);
}

/**
 * @param {object} extension
 */
export function useSubEnv(extension) {
    const component = getCurrentNode().component;
    component.env = extendEnv(extension);
}

/**
 * @param {object} extension
 */
export function useChildSubEnv(extension) {
    extendEnv(extension);
}

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
                const target = document.querySelector(node.props.selector);
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

const customDirectives = {
    /**
     * @param {HTMLElement} node
     * @param {string} value
     */
    ref: (node, value) => {
        const refName = `"` + value.replaceAll(/\{\{(.+?)\}\}/g, `" + $1 + "`) + `"`;
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
        node.setAttribute("selector", value);
    },
};

const globalValues = {
    /**
     * @param {any} component
     * @param {string} refName
     */
    createRefSignal: (component, refName) => ({
        /** @param {HTMLElement | null} value */
        set(value) {
            if (!component.__owl__.__refs__) {
                component.__owl__.__refs__ = {};
            }
            component.__owl__.__refs__[refName] = value;
        },
    }),
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
            component = class extends component {
                constructor(node) {
                    super(node);
                    this.env = provideEnv(config.env);
                }
            };
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
