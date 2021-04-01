/** @odoo-module **/
import { useService } from "../core/hooks";
const { hooks } = owl;
const { onMounted, onWillUnmount } = hooks;

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
  let token;
  onMounted(() => {
    token = commandService.registerCommand(command);
  });
  onWillUnmount(() => {
    commandService.unregisterCommand(token);
  });
}
