odoo.define("@odoo/owl", [], function () {
    "use strict";

    // COMPATIBILITY LAYER ------------------------------------------------------

    const { proxy, useEffect } = owl;
    // useState
    // owl.useState = owl.proxy;

    // reactive
    owl.reactive = function(value, cb) {
        if (cb) {
            // depreciation warning => probably require manual code update
            // console.warn("reactive is deprecated");
            // let called = false;
            // useEffect(() => {
            //     cb()
            // });
        }
        return proxy(value);
    }

    owl.validate = function(value, schema) {
        // todo: reimplement some parts of owl 2 validation code here
    }
    // class EnvPlugin extends Plugin {
    // env = {};
    // }

    // const useEnv = () => plugin(EnvPlugin).env;
    // owl.useEnv = useEnv;

    // owl.useSubEnv = function (extension) {
    // const env = useEnv();
    // const subEnv = Object.assign(Object.create(env), extension);
    // class SubEnvPlugin extends Plugin {
    //     static id = "EnvPlugin";
    //     env = subEnv;
    // }
    // providePlugins([SubEnvPlugin]);
    // }

    // owl.onWillRender = (cb) => {
    //     // find a way to make it work
    // }

    // owl.onRendered = (cb) => {
    //     // find a way to make it work
    // }

    // owl.useComponent = () => {
    //     ...
    // }
    // owl.useExternalListener = ... // duplicate current code from owl

    // owl.Component = class Component extends owl.Component {
    //     constructor(p, e, node) {
    //         super(p, e, node);
    //     }
    // };

    // COMPATIBILITY LAYER ------------------------------------------------------

    return owl;
});
