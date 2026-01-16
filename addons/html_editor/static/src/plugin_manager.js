import { resourceSequenceSymbol, withSequence } from "./utils/resource";

/**
 * @typedef {typeof import("./plugin").Plugin} PluginConstructor
 **/

/**
 * @typedef { Object } PluginManagerConfig
 * @property { PluginConstructor[] } [Plugins]
 * @property { Object } [resources]
 *
 * @typedef { Object } PluginManagerContext
 * @property { Object } dependencies
 * @property { PluginManagerConfig } config
 * @property { * } services
 * @property { PluginManager['getResource'] } getResource
 * @property { PluginManager['dispatchTo'] } dispatchTo
 * @property { PluginManager['delegateTo'] } delegateTo
 */

/**
 * @param {PluginConstructor[]} plugins
 * @returns {PluginConstructor[]}
 */
function sortPlugins(plugins) {
    const initialPlugins = new Set(plugins);
    const inResult = new Set();
    // need to sort them
    const result = [];
    let P;

    function findPlugin() {
        for (const P of initialPlugins) {
            if (P.dependencies.every((dep) => inResult.has(dep))) {
                initialPlugins.delete(P);
                return P;
            }
        }
    }
    while ((P = findPlugin())) {
        inResult.add(P.id);
        result.push(P);
    }
    if (initialPlugins.size) {
        const messages = [];
        for (const P of initialPlugins) {
            messages.push(
                `"${P.id}" is missing (${P.dependencies
                    .filter((d) => !inResult.has(d))
                    .join(", ")})`
            );
        }
        throw new Error(`Missing dependencies:  ${messages.join(", ")}`);
    }
    return result;
}

/**
 * Abstract class to handle Plugins
 * @see Editor
 */
export class PluginManager {
    /**
     * @param { PluginManagerConfig } config
     */
    constructor(config = {}, services = {}) {
        this.pluginPropertyName = "__pluginManager";
        this.isReady = false;
        this.isDestroyed = false;
        this.config = config;
        this.services = services;
        this.setup();
    }

    setup() {
        this.resources = null;
        this.plugins = [];
        this.shared = {};
    }

    /**
     * @return { PluginManagerContext }
     */
    getPluginContext(dependencies = []) {
        return {
            dependencies: this.getDependencies(dependencies),
            config: this.config,
            services: this.services,
            getResource: this.getResource.bind(this),
            dispatchTo: this.dispatchTo.bind(this),
            delegateTo: this.delegateTo.bind(this),
        };
    }

    getDependencies(dependencies) {
        const deps = {};
        for (const depName of dependencies) {
            if (!(depName in this.shared)) {
                throw new Error(`Missing dependency: ${depName}`);
            }
            deps[depName] = this.shared[depName];
        }
        return deps;
    }

    preparePlugins() {
        const Plugins = sortPlugins(this.config.Plugins);
        this.config = Object.assign({}, ...Plugins.map((P) => P.defaultConfig), this.config);
        this.pluginsMap = new Map();
        for (const P of Plugins) {
            if (P.id === "") {
                throw new Error(`Missing plugin id (class ${P.name})`);
            }
            if (this.pluginsMap.has(P.id)) {
                throw new Error(`Duplicate plugin id: ${P.id}`);
            }
            this.pluginsMap.set(P.id, P);
            const plugin = new P(this.getPluginContext(P.dependencies));
            plugin[this.pluginPropertyName] = this;
            this.plugins.push(plugin);
            const exports = {};
            for (const h of P.shared) {
                if (!(h in plugin)) {
                    throw new Error(`Missing helper implementation: ${h} in plugin ${P.id}`);
                }
                exports[h] = plugin[h].bind(plugin);
            }
            this.shared[P.id] = exports;
        }
        const resources = this.createResources();
        for (const plugin of this.plugins) {
            plugin._resources = resources;
        }
        this.resources = resources;
    }

    startPlugins() {
        for (const plugin of this.plugins) {
            plugin.setup();
        }
    }

    createResources() {
        const resources = {};

        function registerResources(obj) {
            for (const key in obj) {
                if (!(key in resources)) {
                    resources[key] = [];
                }
                resources[key].push(obj[key]);
            }
        }
        if (this.config.resources) {
            registerResources(this.config.resources);
        }
        for (const plugin of this.plugins) {
            if (plugin.resources) {
                registerResources(plugin.resources);
            }
        }

        for (const key in resources) {
            const resource = resources[key]
                .flat()
                .map((r) => {
                    const isObjectWithSequence =
                        typeof r === "object" && r !== null && resourceSequenceSymbol in r;
                    return isObjectWithSequence ? r : withSequence(10, r);
                })
                .sort((a, b) => a[resourceSequenceSymbol] - b[resourceSequenceSymbol])
                .map((r) => r.object);

            resources[key] = resource;
            Object.freeze(resources[key]);
        }

        return Object.freeze(resources);
    }

    /**
     * @template {GlobalResourcesId} R
     * @param {R} resourceId
     * @returns {GlobalResources[R]}
     */
    getResource(resourceId) {
        return this.resources[resourceId] || [];
    }

    /**
     * Execute the functions registered under resourceId with the given
     * arguments.
     *
     * This function is meant to enhance code readability by clearly expressing
     * its intent.
     *
     * This function can be thought as an event dispatcher, calling the handlers
     * with `args` as the payload.
     *
     * Example:
     * ```js
     * this.dispatchTo("my_event_handlers", arg1, arg2);
     * ```
     *
     * @template {GlobalResourcesId} R
     * @param {R} resourceId
     * @param {Parameters<GlobalResources[R][0]>} args The arguments to pass to the handlers.
     */
    dispatchTo(resourceId, ...args) {
        this.getResource(resourceId).forEach((handler) => handler(...args));
    }

    /**
     * Execute a series of functions until one of them returns a truthy value.
     *
     * This function is meant to enhance code readability by clearly expressing
     * its intent.
     *
     * A command "delegates" its execution to one of the overriding functions,
     * which return a truthy value to signal it has been handled.
     *
     * It is the the caller's responsability to stop the execution when this
     * function returns true.
     *
     * Example:
     * ```js
     * if (this.delegateTo("my_command_overrides", arg1, arg2)) {
     *   return;
     * }
     * ```
     *
     * @template {GlobalResourcesId} R
     * @param {R} resourceId
     * @param {Parameters<GlobalResources[R][0]>} args The arguments to pass to the overrides.
     * @returns {boolean} Whether one of the overrides returned a truthy value.
     */
    delegateTo(resourceId, ...args) {
        return this.getResource(resourceId).some((fn) => fn(...args));
    }

    destroy() {
        this.isReady = false;
        let plugin;
        while ((plugin = this.plugins.pop())) {
            plugin.destroy();
        }
        this.isDestroyed = true;
    }
}
