/** @odoo-module **/
import { serviceRegistry } from "../webclient/service_registry";
import { isMacOS } from "../core/browser";

export function getHotkeyToPress(hotkey, altIsOptional = false) {
  let result = hotkey.split("+");
  if (isMacOS()) {
    result = result.map((x) => x.replace("control", "command"));
  }
  if (!altIsOptional) {
    result = isMacOS() ? ["control", ...result] : ["alt", ...result];
  }
  return result.join("+");
}

const ALPHANUM_KEYS = "abcdefghijklmnopqrstuvwxyz0123456789".split("");
const NAV_KEYS = [
  "arrowleft",
  "arrowright",
  "arrowup",
  "arrowdown",
  "pageup",
  "pagedown",
  "home",
  "end",
  "backspace",
  "enter",
  "escape",
];
const MODIFIERS = new Set(["control", "shift"]);
const AUTHORIZED_KEYS = new Set([...ALPHANUM_KEYS, ...NAV_KEYS]);

export const hotkeyService = {
  dependencies: ["ui"],
  deploy(env) {
    const { ui } = env.services;
    const registrations = new Map();
    let nextToken = 0;
    let overlaysVisible = false;

    window.addEventListener("keydown", onKeydown);
    window.addEventListener("keyup", removeHotkeyOverlays);
    window.addEventListener("blur", removeHotkeyOverlays);
    window.addEventListener("click", removeHotkeyOverlays);

    /**
     * Handler for keydown events.
     * Verifies if the keyboard event can be dispatched or not.
     * Rules sequence to forbid dispatching :
     * - UI is blocked
     * - the pressed key is not whitelisted
     *
     * @param {KeyboardEvent} event
     */
    function onKeydown(event) {
      const hotkey = getActiveHotkey(event);

      // Do not dispatch if UI is blocked
      if (ui.isBlocked) {
        return;
      }

      // FIXME : this is a temporary hack. It replaces all [accesskey] attrs by [data-hotkey] on all elements.
      const elementsWithoutDataHotkey = ui.getVisibleElements("[accesskey]:not([data-hotkey])");
      for (const el of elementsWithoutDataHotkey) {
        el.dataset.hotkey = el.accessKey;
        el.removeAttribute("accesskey");
      }

      // Special case: open hotkey overlays
      if (isMacOS() ? hotkey === "control" : hotkey === "alt") {
        addHotkeyOverlays();
        event.preventDefault();
        return;
      }

      // Is the pressed key NOT whitelisted ?
      const singleKey = hotkey.split("+").pop();
      if (!AUTHORIZED_KEYS.has(singleKey)) {
        return;
      }

      // Finally, prepare and dispatch.
      const infos = {
        hotkey,
        _originalEvent: event,
      };
      dispatch(infos);
      removeHotkeyOverlays();
    }

    /**
     * Dispatches an hotkey to all matching registrations and
     * clicks on all elements having a data-hotkey attribute matching the hotkey.
     *
     * @param {{
     *  hotkey: string,
     *  _originalEvent: KeyboardEvent
     * }} infos
     */
    function dispatch(infos) {
      let dispatched = false;
      const { hotkey, _originalEvent: event } = infos;
      const isAlted = isMacOS() ? event.ctrlKey : event.altKey;
      const activeElement = ui.activeElement;

      // Dispatch actual hotkey to all matching registrations
      for (const [_, reg] of registrations) {
        if (!reg.global && reg.activeElement !== activeElement) {
          continue;
        }

        if (reg.hotkey !== hotkey) {
          continue;
        }

        if (!reg.altIsOptional && !isAlted) {
          continue;
        }

        if (!reg.allowRepeat && event.repeat) {
          continue;
        }

        reg.callback();
        dispatched = true;
      }

      if (!event.repeat && isAlted) {
        // Click on all elements having a data-hotkey attribute matching the actual hotkey.
        const elems = activeElement.querySelectorAll(`[data-hotkey='${hotkey}' i]`);
        for (const el of elems) {
          // AAB: not sure it is enough, we might need to trigger all events that occur when you actually click
          el.focus();
          el.click();
          dispatched = true;
        }
      }

      // Prevent default on event if it has been handheld.
      if (dispatched) {
        event.preventDefault();
      }
    }

    /**
     * Add the hotkey overlays respecting the ui active element.
     */
    function addHotkeyOverlays() {
      if (overlaysVisible) {
        return;
      }
      for (const el of env.services.ui.getVisibleElements("[data-hotkey]:not(:disabled)")) {
        const hotkey = el.dataset.hotkey;
        const overlay = document.createElement("div");
        overlay.className = "o_web_hotkey_overlay";
        overlay.appendChild(document.createTextNode(hotkey.toUpperCase()));

        let overlayParent;
        if (el.tagName.toUpperCase() === "INPUT") {
          // special case for the search input that has an access key
          // defined. We cannot set the overlay on the input itself,
          // only on its parent.
          overlayParent = el.parentElement;
        } else {
          overlayParent = el;
        }

        if (overlayParent.style.position !== "absolute") {
          overlayParent.style.position = "relative";
        }
        overlayParent.appendChild(overlay);
      }
      overlaysVisible = true;
    }

    /**
     * Remove all the hotkey overlays.
     */
    function removeHotkeyOverlays() {
      if (!overlaysVisible) {
        return;
      }
      for (const overlay of document.querySelectorAll(".o_web_hotkey_overlay")) {
        overlay.remove();
      }
      overlaysVisible = false;
    }

    /**
     * Get the actual hotkey being pressed.
     *
     * @param {KeyboardEvent} ev
     * @returns {string} the active hotkey, in lowercase
     */
    function getActiveHotkey(ev) {
      const hotkey = [];

      // ------- Modifiers -------
      // Modifiers are pushed in ascending order to the hotkey.
      if (isMacOS() ? ev.metaKey : ev.ctrlKey) {
        hotkey.push("control");
      }
      if (ev.shiftKey) {
        hotkey.push("shift");
      }

      // ------- Key -------
      let key = ev.key.toLowerCase();
      // Identify if the user has tapped on the number keys above the text keys.
      if (ev.code && ev.code.indexOf("Digit") === 0) {
        key = ev.code.slice(-1);
      }
      // Make sure we do not duplicate a modifier key
      if (!hotkey.includes(key)) {
        hotkey.push(key);
      }

      return hotkey.join("+");
    }

    /**
     * Registers a new hotkey.
     *
     * @param {string} hotkey
     * @param {()=>void} callback
     * @param {Object} options additional options
     * @param {boolean} [options.altIsOptional=false]
     *  allow registration to perform even without pressing the ALT key
     * @param {boolean} [options.allowRepeat=false]
     *  allow registration to perform multiple times when hotkey is held down
     * @param {boolean} [options.global=false]
     *  allow registration to perform no matter the UI active element
     * @returns {number} registration token
     */
    function registerHotkey(hotkey, callback, options = {}) {
      // Validate some informations
      if (!hotkey || hotkey.length === 0) {
        throw new Error("You must specify an hotkey when registering a registration.");
      }

      if (!callback || typeof callback !== "function") {
        throw new Error("You must specify a callback function when registering a registration.");
      }

      /**
       * An hotkey must comply to these rules:
       *  - all parts are whitelisted
       *  - single key part comes last
       *  - each part is separated by the dash character: "+"
       */
      const keys = hotkey
        .toLowerCase()
        .split("+")
        .filter((k) => !MODIFIERS.has(k));
      if (keys.some((k) => !AUTHORIZED_KEYS.has(k))) {
        throw new Error(
          `You are trying to subscribe for an hotkey ('${hotkey}')
            that contains parts not whitelisted: ${keys.join(", ")}`
        );
      } else if (keys.length > 1) {
        throw new Error(
          `You are trying to subscribe for an hotkey ('${hotkey}')
            that contains more than one single key part: ${keys.join("+")}`
        );
      }

      // Add registration
      const token = nextToken++;
      const registration = {
        hotkey: hotkey.toLowerCase(),
        callback,
        activeElement: null,
        altIsOptional: options && options.altIsOptional,
        allowRepeat: options && options.allowRepeat,
        global: options && options.global,
      };
      registrations.set(token, registration);

      // Due to the way elements are mounted in the DOM by Owl (bottom-to-top),
      // we need to wait the next micro task tick to set the context owner of the registration.
      Promise.resolve().then(() => {
        registration.activeElement = ui.activeElement;
      });

      return token;
    }

    /**
     * Unsubscribes the token corresponding registration.
     *
     * @param {number} token
     */
    function unregisterHotkey(token) {
      registrations.delete(token);
    }

    return {
      registerHotkey,
      unregisterHotkey,
    };
  },
};

serviceRegistry.add("hotkey", hotkeyService);
