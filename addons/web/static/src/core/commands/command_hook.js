/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

import { useEffect } from "@odoo/owl";

/**
 * @typedef {import("./command_service").CommandOptions} CommandOptions
 */

/**
 * This hook will subscribe/unsubscribe the given subscription
 * when the caller component will mount/unmount.
 *
 * @param {string} name
 * @param {()=>(void | CommandPaletteConfig)} action
 * @param {CommandOptions} [options]
 */
export function useCommand(name, action, options = {}) {
    const commandService = useService("command");
    useEffect(
        () => commandService.add(name, action, options),
        () => []
    );
}
