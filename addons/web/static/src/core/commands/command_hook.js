import { useLayoutEffect } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";


/**
 * @typedef {import("./command_service").CommandOptions} CommandOptions
 */

/**
 * This hook will subscribe/unsubscribe the given subscription
 * when the caller component will mount/unmount.
 *
 * @param {string} name
 * @param {()=>(void | import("@web/core/commands/command_palette").CommandPaletteConfig)} action
 * @param {CommandOptions} [options]
 */
export function useCommand(name, action, options = {}) {
    const commandService = useService("command");
    useLayoutEffect(
        () => commandService.add(name, action, options),
        () => []
    );
}
