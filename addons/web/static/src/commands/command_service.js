/** @odoo-module **/
import { getHotkeyToPress } from "../hotkey/hotkey_service";
import { serviceRegistry } from "../webclient/service_registry";
import { CommandPaletteDialog } from "./command_palette_dialog";

/**
 * @typedef {{
 *  name: string,
 *  action: ()=>void,
 *  category?: string,
 *  hotkey?: string,
 *  hotkeyOptions?: any,
 * }} Command
 */

export const commandService = {
  dependencies: ["dialog", "hotkey", "ui"],
  deploy(env) {
    const { dialog, hotkey: hotkeyService, ui } = env.services;
    const registeredCommands = new Map();
    let nextToken = 0;
    let isPaletteOpened = false;

    hotkeyService.registerHotkey("control+k", openPalette, { altIsOptional: true, global: true });

    function openPalette() {
      if (isPaletteOpened) {
        return;
      }

      const commands = [...registeredCommands.values()];

      // Also retrieve all hotkeyables elements
      for (const el of ui.getVisibleElements("[data-hotkey]:not(:disabled)")) {
        const closest = el.closest("[data-command-category]");
        const category = closest ? closest.dataset.commandCategory : "default";

        const description =
          el.title ||
          el.placeholder ||
          (el.innerText &&
            `${el.innerText.slice(0, 50)}${el.innerText.length > 50 ? "..." : ""}`) ||
          "no description provided";

        commands.push({
          name: description,
          hotkey: getHotkeyToPress(el.dataset.hotkey),
          action: () => {
            // AAB: not sure it is enough, we might need to trigger all events that occur when you actually click
            el.focus();
            el.click();
          },
          category,
        });
      }

      // Open palette dialog
      isPaletteOpened = true;
      dialog.open(
        CommandPaletteDialog,
        { commands },
        {
          onCloseCallback: () => {
            isPaletteOpened = false;
          },
        }
      );
    }

    /**
     * @param {Command} command
     * @returns {number} token
     */
    function registerCommand(command) {
      if (!command.name || !command.action || typeof command.action !== "function") {
        throw new Error("A Command must have a name and an action function.");
      }

      const registration = Object.assign({}, command, { activeElement: null });

      if (command.hotkey) {
        registration.hotkeyToken = hotkeyService.registerHotkey(
          command.hotkey,
          command.action,
          command.hotkeyOptions
        );
        const altIsOptional = command.hotkeyOptions && command.hotkeyOptions.altIsOptional;
        registration.hotkey = getHotkeyToPress(command.hotkey, altIsOptional);
      }

      const token = nextToken++;
      registeredCommands.set(token, registration);

      // Due to the way elements are mounted in the DOM by Owl (bottom-to-top),
      // we need to wait the next micro task tick to set the context activate
      // element of the subscription.
      Promise.resolve().then(() => {
        registration.activeElement = ui.activeElement;
      });

      return token;
    }

    /**
     * Unsubscribes the token corresponding subscription.
     *
     * @param {number} token
     */
    function unregisterCommand(token) {
      const cmd = registeredCommands.get(token);
      if (cmd && cmd.hotkeyToken >= 0) {
        env.services.hotkey.unregisterHotkey(cmd.hotkeyToken);
      }
      registeredCommands.delete(token);
    }

    return {
      registerCommand,
      unregisterCommand,
    };
  },
};

serviceRegistry.add("command", commandService);
