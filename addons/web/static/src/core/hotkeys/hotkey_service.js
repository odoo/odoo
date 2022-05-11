/** @odoo-module **/

import { isMacOS } from "../browser/feature_detection";
import { registry } from "../registry";
import { browser } from "../browser/browser";
import { getVisibleElements } from "../utils/ui";

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
    "tab",
    "delete",
];
const MODIFIERS = new Set(["alt", "control", "shift"]);
const AUTHORIZED_KEYS = new Set([...ALPHANUM_KEYS, ...NAV_KEYS, "escape"]);

export const hotkeyService = {
    dependencies: ["ui"],
    // Be aware that all odoo hotkeys are designed with this modifier in mind,
    // so changing the overlay modifier may conflict with some shortcuts.
    overlayModifier: "alt",
    start(env, { ui }) {
        const registrations = new Map();
        let nextToken = 0;
        let overlaysVisible = false;

        addListeners(browser);

        function addListeners(target) {
            target.addEventListener("keydown", onKeydown);
            target.addEventListener("keyup", removeHotkeyOverlays);
            target.addEventListener("blur", removeHotkeyOverlays);
            target.addEventListener("click", removeHotkeyOverlays);
        }

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
            if (!event.key) {
                // Chrome may trigger incomplete keydown events under certain circumstances.
                // E.g. when using browser built-in autocomplete on an input.
                // See https://stackoverflow.com/questions/59534586/google-chrome-fires-keydown-event-when-form-autocomplete
                return;
            }

            if (event.code && event.code.indexOf("Numpad") === 0 && /^\d$/.test(event.key)) {
                // Ignore all number keys from the Keypad because of a certain input method
                // of (advance-)ASCII characters on Windows OS: ALT+[numerical code from keypad]
                // See https://support.microsoft.com/en-us/office/insert-ascii-or-unicode-latin-based-symbols-and-characters-d13f58d3-7bcb-44a7-a4d5-972ee12e50e0#bm1
                return;
            }

            const hotkey = getActiveHotkey(event);

            // Do not dispatch if UI is blocked
            if (ui.isBlocked) {
                return;
            }

            // Replace all [accesskey] attrs by [data-hotkey] on all elements.
            // This is needed to take over on the default accesskey behavior
            // and also to avoid any conflict with it.
            const elementsWithAccessKey = document.querySelectorAll("[accesskey]");
            for (const el of elementsWithAccessKey) {
                if (el instanceof HTMLElement) {
                    el.dataset.hotkey = el.accessKey;
                    el.removeAttribute("accesskey");
                }
            }

            // Special case: open hotkey overlays
            if (hotkey === hotkeyService.overlayModifier) {
                addHotkeyOverlays();
                event.preventDefault();
                return;
            }

            // Is the pressed key NOT whitelisted ?
            const singleKey = hotkey.split("+").pop();
            if (!AUTHORIZED_KEYS.has(singleKey)) {
                return;
            }

            // Protect any editable target that does not explicitly accept hotkeys
            // NB: except for ESC, which is always allowed as hotkey in editables.
            const targetIsEditable =
                event.target instanceof HTMLElement &&
                (/input|textarea/i.test(event.target.tagName) || event.target.isContentEditable);
            const shouldProtectEditable =
                targetIsEditable && !event.target.dataset.allowHotkeys && singleKey !== "escape";

            // Finally, prepare and dispatch.
            const infos = {
                hotkey,
                shouldProtectEditable,
                _originalEvent: event,
            };
            dispatch(infos);
            removeHotkeyOverlays(event);
        }

        /**
         * Dispatches an hotkey to first matching registration.
         * Registrations are iterated in following order:
         * - priority to all registrations done through the hotkeyService.add()
         *   method (NB: in descending order of insertion = newer first)
         * - then all registrations done through the DOM [data-hotkey] attribute
         *
         * @param {{
         *  hotkey: string,
         *  shouldProtectEditable: boolean,
         *  _originalEvent: KeyboardEvent
         * }} infos
         */
        function dispatch(infos) {
            let dispatched = false;
            const { hotkey, shouldProtectEditable, _originalEvent: event } = infos;
            const activeElement = ui.activeElement;

            // Dispatch actual hotkey to all matching registrations
            for (const reg of Array.from(registrations.values()).reverse()) {
                if (!reg.global && reg.activeElement !== activeElement) {
                    continue;
                }

                if (reg.hotkey !== hotkey) {
                    continue;
                }

                if (!reg.allowRepeat && event.repeat) {
                    continue;
                }

                if (!reg.bypassEditableProtection && shouldProtectEditable) {
                    continue;
                }

                reg.callback();
                dispatched = true;
                break;
            }
            const overlayModParts = hotkeyService.overlayModifier.split("+");
            if (
                !dispatched &&
                !event.repeat &&
                overlayModParts.every((el) => hotkey.includes(el))
            ) {
                // Click on all elements having a data-hotkey attribute matching the actual hotkey without the overlayModifier.
                const cleanHotkey = hotkey
                    .split("+")
                    .filter((key) => !overlayModParts.includes(key))
                    .join("+");
                const elems = getVisibleElements(
                    ui.activeElement,
                    `[data-hotkey='${cleanHotkey}' i]`
                );
                for (const el of elems) {
                    // AAB: not sure it is enough, we might need to trigger all events that occur when you actually click
                    el.focus();
                    el.click();
                    dispatched = true;
                    break;
                }
            }

            // Only if event has been handheld.
            if (dispatched) {
                // Purpose: prevent browser defaults
                event.preventDefault();
                // Purpose: stop other window keydown listeners (e.g. home menu)
                event.stopImmediatePropagation();
            }
        }

        /**
         * Add the hotkey overlays respecting the ui active element.
         */
        function addHotkeyOverlays() {
            if (overlaysVisible) {
                return;
            }
            for (const el of getVisibleElements(ui.activeElement, "[data-hotkey]:not(:disabled)")) {
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
        function removeHotkeyOverlays(event) {
            if (!overlaysVisible) {
                return;
            }
            for (const overlay of document.querySelectorAll(".o_web_hotkey_overlay")) {
                overlay.remove();
            }
            overlaysVisible = false;
            event.preventDefault();
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
            if (isMacOS() ? ev.ctrlKey : ev.altKey) {
                hotkey.push("alt");
            }
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
            // Prefer physical keys for non-latin keyboard layout.
            if (!AUTHORIZED_KEYS.has(key) && ev.code && ev.code.indexOf("Key") === 0) {
                key = ev.code.slice(-1).toLowerCase();
            }
            // Make sure we do not duplicate a modifier key
            if (!MODIFIERS.has(key)) {
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
         * @param {boolean} [options.allowRepeat=false]
         *  allow registration to perform multiple times when hotkey is held down
         * @param {boolean} [options.bypassEditableProtection=false]
         *  if true the hotkey service will call this registration
         *  even if an editable element is focused
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
                throw new Error(
                    "You must specify a callback function when registering a registration."
                );
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
                allowRepeat: options && options.allowRepeat,
                bypassEditableProtection: options && options.bypassEditableProtection,
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
            /**
             * @param {string} hotkey
             * @param {() => void} callback
             * @param {Object} options
             * @param {boolean} [options.allowRepeat=false]
             * @param {boolean} [options.bypassEditableProtection=false]
             * @param {boolean} [options.global=false]
             * @returns {() => void}
             */
            add(hotkey, callback, options = {}) {
                const token = registerHotkey(hotkey, callback, options);
                return () => {
                    unregisterHotkey(token);
                };
            },
            /**
             * @param {HTMLIFrameElement} iframe
             */
            registerIframe(iframe) {
                addListeners(iframe.contentWindow);
            },
        };
    },
};

registry.category("services").add("hotkey", hotkeyService);
