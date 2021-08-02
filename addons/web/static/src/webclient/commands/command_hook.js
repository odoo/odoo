/** @odoo-module **/

import { useEffect, useService } from "@web/core/utils/hooks";

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
