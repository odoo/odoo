/** @odoo-module **/

import { useEffect } from "@web/core/effect_hook";
import { useService } from "@web/core/service_hook";

/**
 * @typedef {import("./command_service").CommandServiceAddOptions} CommandServiceAddOptions
 */

/**
 * This hook will subscribe/unsubscribe the given subscription
 * when the caller component will mount/unmount.
 *
 * @param {string} name
 * @param {() => void} action
 * @param {CommandServiceAddOptions} [options]
 */
export function useCommand(name, action, options = {}) {
    const commandService = useService("command");
    useEffect(
        () => commandService.add(name, action, options),
        () => []
    );
}
