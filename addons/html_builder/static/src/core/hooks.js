import { usePlugin, useScope } from "@odoo/owl";

/**
 * Version of usePlugin() where the plugin is allowed to not be provided by any parented component.
 *
 * @template T
 * @param {T extends import("@odoo/owl").PluginConstructor} pluginType
 * @returns {import("@odoo/owl").PluginInstance<T>|undefined}
 */
export function useMaybePlugin(pluginType) {
    if (useScope().pluginManager?.getPluginById(pluginType.id)) {
        return usePlugin(pluginType);
    }
    return undefined;
}
