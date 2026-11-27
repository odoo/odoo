import { sortPlugins } from "@html_editor/plugin_utils";
import { resourceSequenceSymbol, withSequence } from "@html_editor/utils/resource";

/**
 * Abstract class to handle Plugins
 * @see Editor
 */
export class PluginManager {
    /**
     * @param { PluginManagerConfig } config
     */
    constructor(scope) {
        this.scope = scope;
        this.pluginPropertyName = "__pluginManager";
        this.isReady = false;
        this.isDestroyed = false;
        this.config = {};
        this.plugins = [];
        this.resources = null;
        this.shared = {};
        // Map each function exposed by a plugin (shared function or resource
        // entry) to the id of the plugin defining it.
        this.functionOwners = new WeakMap();
    }

    /**
     * @return { PluginManagerContext }
     */
    getPluginContext(dependencies = []) {
        return {
            config: this.config,
            dependencies: this.getDependencies(dependencies),
            getResource: this.getResource.bind(this),
            trigger: this.trigger.bind(this),
            triggerAsync: this.triggerAsync.bind(this),
            delegateTo: this.delegateTo.bind(this),
            processRules: this.processRules.bind(this),
            processThrough: this.processThrough.bind(this),
            checkPredicates: this.checkPredicates.bind(this),
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
            plugin.assignShared();
            this.plugins.push(plugin);
            const exports = {};
            for (const h of P.shared) {
                if (!(h in plugin)) {
                    throw new Error(`Missing helper implementation: ${h} in plugin ${P.id}`);
                }
                exports[h] = plugin[h].bind(plugin);
                this.functionOwners.set(exports[h], P.id);
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
        this.scope.run(() => {
            for (const plugin of this.plugins) {
                plugin.setup();
            }
        });
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
                this.registerFunctionOwners(plugin.resources, plugin.constructor.id);
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
     * Register `pluginId` as the owner of every function found in `resources`.
     *
     * @param {Object} resources
     * @param {string} pluginId
     */
    registerFunctionOwners(resources, pluginId) {
        for (const entry of Object.values(resources).flat()) {
            const isObjectWithSequence =
                typeof entry === "object" && entry !== null && resourceSequenceSymbol in entry;
            const fn = isObjectWithSequence ? entry.object : entry;
            if (typeof fn === "function" && !this.functionOwners.has(fn)) {
                this.functionOwners.set(fn, pluginId);
            }
        }
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
     * Execute the handler functions registered under resourceId with the given
     * arguments, and return an array containing all their return values.
     *
     * This function is meant to enhance code readability by clearly expressing
     * its intent.
     *
     * Examples:
     * ```js
     * const values = this.trigger("on_my_event_handlers", arg1, arg2);
     * await Promise.all(this.trigger("on_my_async_event_handlers", arg1, arg2));
     * ```
     *
     * @template {GlobalResourcesId} R
     * @param {R} resourceId
     * @param {Parameters<GlobalResources[R][0]>} args The arguments to pass to the handlers.
     * @returns {Array<any>}
     */
    trigger(resourceId, ...args) {
        return this.getResource(resourceId).map((handler) => handler(...args));
    }

    /**
     * Execute the handler functions registered under resourceId with the given
     * arguments sequentially, waiting for each call to resolve before calling
     * the next.
     *
     * This function is meant to enhance code readability by clearly expressing
     * its intent.
     *
     * Example:
     * ```js
     * await this.triggerAsync("on_my_sequential_async_event_handlers", arg1, arg2);
     * ```
     *
     * @template {GlobalResourcesId} R
     * @param {R} resourceId
     * @param {Parameters<GlobalResources[R][0]>} args The arguments to pass to the handlers.
     * @returns {Promise<void>}
     */
    async triggerAsync(resourceId, ...args) {
        for (const handler of this.getResource(resourceId)) {
            await handler(...args);
        }
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

    /**
     * Fill `rules` with every provider registered under resourceId. Each
     * provider receives a view of `rules` which assigns the id of the plugin
     * defining the provider as the origin of every created Rule, for easier
     * debugging.
     *
     * @template {GlobalResourcesId} R
     * @param {R} resourceId
     * @param {Rules} rules
     * @returns {Rules} `rules`
     */
    processRules(resourceId, rules) {
        for (const provider of this.getResource(resourceId)) {
            provider(rules.forPlugin(this.functionOwners.get(provider)));
        }
        return rules;
    }

    /**
     * Execute a series of functions that each process an item, and return its
     * final value.
     *
     * This function is meant to enhance code readability by clearly expressing
     * its intent.
     *
     * An item is processed by each processor in sequence, each processor
     * returning the new value of the item. Processors mutating the item in
     * place must return that item.
     *
     * Example:
     * ```js
     * const processedItem = this.processThrough("my_item_processors", item, arg1, arg2);
     * ```
     *
     * @template {GlobalResourcesId} R
     * @param {R} resourceId
     * @param {Parameters<GlobalResources[R][0]>[0]} item The item to process.
     * @param  {Parameters<GlobalResources[R][0]>} args The other arguments to pass to the processors.
     * @returns {Parameters<GlobalResources[R][0]>[0]} The processed value of the item.
     */
    processThrough(resourceId, item, ...args) {
        this.getResource(resourceId).forEach((processor) => {
            item = processor(item, ...args);
        });
        return item;
    }

    /**
     * Test the given arguments against all the predicates registered under
     * `resourceId` (which ends with "_predicates" by convention), and return
     * true if any predicate returns `true` and none returns `false` (ignoring
     * those that return `undefined`).
     *
     * Important note: since this function treats booleans and nullish results
     * differently, make sure that:
     * 1. Predicates only return a boolean when it's meaningful.
     * 2. Any call to `checkPredicates` involves the declaration of a default
     *    value in case it returns `undefined`.
     *
     * Example:
     * ```js
     * const isTrue = this.checkPredicates("is_it_true_predicates", arg1, arg2) ?? true;
     * ```
     *
     * @param {string} resourceId
     * @param  {...any} args The arguments to pass to the predicates.
     * @returns {boolean | undefined}
     */
    checkPredicates(resourceId, ...args) {
        const results = this.getResource(resourceId)
            .map((predicate) => predicate(...args))
            .filter((result) => result !== undefined);
        return results.length ? results.every(Boolean) : undefined;
    }

    destroy() {
        if (this.isDestroyed) {
            return;
        }
        this.isReady = false;
        let plugin;
        while ((plugin = this.plugins.pop())) {
            plugin.destroy();
        }
        this.isDestroyed = true;
    }
}
