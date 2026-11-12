import { onMounted, onWillUnmount, useScope } from "@odoo/owl";

/**
 * @typedef {import("./command_plugin").CommandOptions} CommandOptions
 */

/**
 * This hook will subscribe/unsubscribe the given subscription
 * when the caller component will mount/unmount.
 *
 * @param {TranslatedString} name
 * @param {()=>(void | import("@web/core/commands/command_palette").CommandPaletteConfig)} action
 * @param {CommandOptions} [options]
 */
export function useCommand(name, action, options = {}) {
    // By id, not by class: this file is also loaded in frontend bundles, which
    // don't include the backend-only CommandPlugin, so its import would fail there.
    const commandService = useScope().pluginManager.getPluginById("CommandPlugin");
    let remove;
    onMounted(() => {
        remove = commandService.add(name, action, options);
    });
    onWillUnmount(() => remove?.());
}
