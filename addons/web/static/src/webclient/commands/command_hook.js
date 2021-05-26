/** @odoo-module **/

import { useService } from "../../core/service_hook";
import { useEffect } from "../../core/effect_hook";

/**
 * @typedef {import("./command_service").Command} Command
 */

/**
 * This hook will subscribe/unsubscribe the given subscription
 * when the caller component will mount/unmount.
 *
 * @param {Command} command
 */
export function useCommand(command) {
    const commandService = useService("command");
    useEffect(() => {
        const token = commandService.registerCommand(command);
        return () => commandService.unregisterCommand(token);
    }, () => []);
}
