// @ts-check

import { stores } from "@odoo/o-spreadsheet";
import {
    App,
    Component,
    providePlugins,
    types,
    usePlugin,
    useProps,
    useScope,
    xml,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const { useStoreProvider } = stores;

/**
 * @typedef {import("@odoo/owl").PluginConstructor} PluginConstructor
 * @typedef {import("@odoo/owl").PluginInstance} PluginInstance
 *
 * @template T
 * @typedef {<T extends PluginConstructor>(plugin: T) => PluginInstance<T>} OwlPluginGetter
 */

/**
 * While we have a mix of owl plugins and stores, some stores use owl plugins with usePlugin called inside
 * their constructor. This only works if the store is created inside an owl scope.
 *
 * This helper change the container to a proxy where every of its method is called inside the given scope.
 *
 * @param {import("@odoo/owl").Scope} scope
 * @param {DependencyContainer} container
 *
 */
export function scopeDependencyContainer(scope, container) {
    return new Proxy(container, {
        get(target, prop, receiver) {
            const value = Reflect.get(target, prop, receiver);

            if (typeof value === "function") {
                return (...args) => scope.run(() => value.apply(target, args));
            }

            return value;
        },
    });
}

class PluginParent extends Component {
    static template = xml/*xml*/ `<div/>`;
    props = useProps({
        providedPlugins: types.array(),
        registerCallback: types.function(),
    });

    setup() {
        providePlugins(this.props.providedPlugins);

        const scope = useScope();
        const getPlugin = createGetPluginFunctionFromScope(scope);
        const container = useStoreProvider();

        this.props.registerCallback({ getPlugin, scope, container });
    }
}

export function makeOwlPluginManager(providedPlugins) {
    const app = new App({ test: true, translateFn: _t });

    let getPlugin = undefined;
    let scope = undefined;
    let container = undefined;

    app.createRoot(PluginParent, {
        props: {
            providedPlugins: providedPlugins,
            registerCallback: (params) => {
                getPlugin = params.getPlugin;
                scope = params.scope;
                container = params.container;
            },
        },
    });

    if (!getPlugin || !scope || !container) {
        throw new Error("Failed to create owl plugin container");
    }

    container = scopeDependencyContainer(scope, container);

    return { getPlugin, scope, container };
}

function createGetPluginFunctionFromScope(scope) {
    return (plugin) => {
        let instance = undefined;
        scope.run(() => (instance = usePlugin(plugin)));
        if (!instance) {
            throw new Error(`Plugin ${plugin.name} not found`);
        }
        return instance;
    };
}
