/**
 * Owl 3 -> 2 Compatibility layer
 *
 * This files monkey patches owl 3 to bring back as many owl 2 behaviours as
 * possible
 */

// @ts-ignore
const owl = globalThis.owl;
const { props, proxy, config, types, plugin, providePlugins } = owl;
const t = types;

// -----------------------------------------------------------------------------
// Preparation
// -----------------------------------------------------------------------------

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
        if (!this.props) {
            this.props = props();
        }
        const envPlugin = plugin(EnvPlugin);
        this.env = envPlugin.env;
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

/**
 * @private
 */
export function _getCurrentNode() {
    if (!currentNode) {
        throw new Error("No current node");
    }
    return currentNode;
}

// -----------------------------------------------------------------------------
// Adding back features
// -----------------------------------------------------------------------------

owl.useState = owl.proxy;
owl.useExternalListener = owl.useListener;

// reactive
owl.reactive = function (value, cb) {
    if (cb) {
        // depreciation warning => probably require manual code update
        // console.warn("reactive is deprecated");
        // let called = false;
        // useEffect(() => {
        //     cb()
        // });
    }
    return proxy(value);
};

/**
 * @deprecated
 */
owl.useComponent = function useComponent() {
    return _getCurrentNode().component;
};

// -----------------------------------------------------------------------------
// Env
// -----------------------------------------------------------------------------

// note: the Env plugin has to be added to an app to make it work

export class EnvPlugin extends owl.Plugin {
    static id = "EnvPlugin";
    env = config("env?", t.object()) || {};
}

owl.useEnv = function useEnv() {
    return _getCurrentNode().component.env;
};

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
    providePlugins([SubEnvPlugin]);
    return subEnv;
}

/**
 * @param {object} extension
 */
owl.useSubEnv = function useSubEnv(extension) {
    const component = _getCurrentNode().component;
    component.env = extendEnv(component.env, extension);
};

// const utils = require("@web/owl2/utils");

// const { proxy, useEffect } = owl;
// // useState
// // owl.useState = owl.proxy;

// // reactive
// owl.reactive = function(value, cb) {
//     if (cb) {
//         // depreciation warning => probably require manual code update
//         // console.warn("reactive is deprecated");
//         // let called = false;
//         // useEffect(() => {
//         //     cb()
//         // });
//     }
//     return proxy(value);
// }

// owl.validate = function(value, schema) {
//     // todo: reimplement some parts of owl 2 validation code here
// }
// // class EnvPlugin extends Plugin {
// // env = {};
// // }

// // const useEnv = () => plugin(EnvPlugin).env;
// // owl.useEnv = useEnv;

// // owl.useSubEnv = function (extension) {
// // const env = useEnv();
// // const subEnv = Object.assign(Object.create(env), extension);
// // class SubEnvPlugin extends Plugin {
// //     static id = "EnvPlugin";
// //     env = subEnv;
// // }
// // providePlugins([SubEnvPlugin]);
// // }

// // owl.onWillRender = (cb) => {
// //     // find a way to make it work
// // }

// // owl.onRendered = (cb) => {
// //     // find a way to make it work
// // }

// owl.useComponent = utils.useComponent;
// // owl.useExternalListener = ... // duplicate current code from owl

// // owl.Component = class Component extends owl.Component {
// //     constructor(p, e, node) {
// //         super(p, e, node);
// //     }
// // };

// // COMPATIBILITY LAYER ------------------------------------------------------
