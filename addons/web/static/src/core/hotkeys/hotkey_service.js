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
    "escape",
    "tab",
    "delete",
];
const MODIFIERS = new Set(["alt", "control", "shift"]);
const AUTHORIZED_KEYS = new Set([...ALPHANUM_KEYS, ...NAV_KEYS]);

export const ANY_HOTKEY = Symbol("ANY_HOTKEY");

export const hotkeyService = {
    dependencies: ["ui"],
    // Be aware that all odoo hotkeys are designed with this modifier in mind,
    // so changing the overlay modifier may conflict with some shortcuts.
    overlayModifier: "alt",
    start(env, { ui }) {
        const registrations = new Map();
        let nextToken = 0;
        let overlaysVisible = false;

        browser.addEventListener("keydown", onKeydown);
        browser.addEventListener("keyup", removeHotkeyOverlays);
        browser.addEventListener("blur", removeHotkeyOverlays);
        browser.addEventListener("click", removeHotkeyOverlays);

        /**
         * Handler for keydown events.
         * Verifies if the keyboard event can be dispatched or not.
         * Rules sequence to forbid dispatching :
         * - UI is blocked
         * - the pressed key is not whitelisted
         *
         * @param {KeyboardEvent} event
         */
        async function onKeydown(event) {
            if (!event.key) {
                // Chrome may trigger incomplete keydown events under certain circumstances.
                // E.g. when using browser built-in autocomplete on an input.
                // See https://stackoverflow.com/questions/59534586/google-chrome-fires-keydown-event-when-form-autocomplete
                return;
            }

            // Do nothing if UI is blocked
            if (ui.isBlocked) {
                return;
            }

            // Prepare infos
            const hotkey = getActiveHotkey(event);
            const activeElement = ui.activeElement;
            const infos = { hotkey, activeElement, event };

            // FIXME : this is a temporary hack. It replaces all [accesskey] attrs by [data-hotkey] on all elements.
            const elementsWithoutDataHotkey = getVisibleElements(
                activeElement,
                "[accesskey]:not([data-hotkey])"
            );
            for (const el of elementsWithoutDataHotkey) {
                el.dataset.hotkey = el.accessKey;
                el.removeAttribute("accesskey");
            }

            // Prepare registrations and the common filter
            const domRegistrations = getDomRegistrations(hotkey, activeElement);
            const allRegistrations = Array.from(registrations.values()).concat(domRegistrations);
            const commonFilter = (reg) =>
                (reg.global || reg.activeElement === activeElement)
                && (reg.hotkey === ANY_HOTKEY || reg.hotkey === hotkey)
                && (reg.allowRepeat || !event.repeat);

            // Capture phase
            let toNotify = allRegistrations.filter((reg) => reg.capture && commonFilter(reg));
            const captured = (await notify(toNotify, infos)).some((res) => res && res.captured);
            if (captured) {
                // Purpose: prevent browser defaults
                event.preventDefault();
                // Purpose: stop other window keydown listeners (e.g. home menu)
                event.stopImmediatePropagation();
                // Purpose: has been captured, hence hotkey service will stop there.
                return;
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

            // Dispatch phase
            toNotify = Array.from(registrations.values()).filter((reg) => !reg.capture && commonFilter(reg));
            const dispatched = (await notify(toNotify, infos)).length > 0;

            // Only if event has been handheld.
            if (dispatched) {
                // Purpose: prevent browser defaults
                event.preventDefault();
                // Purpose: stop other window keydown listeners (e.g. home menu)
                event.stopImmediatePropagation();
            }

            removeHotkeyOverlays(event);
        }

        function notify(registrations, infos) {
            let proms = [];
            for (const reg of registrations) {
                proms.push(reg.callback(infos));
            }
            return Promise.all(proms);
        }

        function getDomRegistrations(hotkey, activeElement) {
            const overlayModParts = hotkeyService.overlayModifier.split("+");
            if (!overlayModParts.every((el) => hotkey.includes(el))) {
                return [];
            }

            // Click on all elements having a data-hotkey attribute matching the actual hotkey without the overlayModifier.
            const cleanHotkey = hotkey
                .split("+")
                .filter((key) => !overlayModParts.includes(key))
                .join("+");
            const elems = getVisibleElements(activeElement, `[data-hotkey='${cleanHotkey}' i]`);
            return elems.map((el) => ({
                hotkey,
                activeElement,
                callback: () => {
                    // AAB: not sure it is enough, we might need to trigger all events that occur when you actually click
                    el.focus();
                    el.click();
                },
            }));
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
         * @param {string | ANY_HOTKEY} hotkey
         * @param {()=>void} callback
         * @param {Object} options additional options
         * @param {boolean} [options.allowRepeat=false]
         *  allow registration to perform multiple times when hotkey is held down
         * @param {boolean} [options.global=false]
         *  allow registration to perform no matter the UI active element
         * @param {boolean} [options.capture=false]
         *  registrations in capture mode would get called beforehand and would
         *  have the opportunity to stop the dispatching of an hotkey by
         *  returning an object `{captured: true}` in order to cancel current dispatching.
         *  Note that the capturer may be asynchronous and could delay the dispatching.
         * @returns {number} registration token
         */
        function registerHotkey(hotkey, callback, options = {}) {
            // Validate some informations
            if (!hotkey) {
                throw new Error("You must specify an hotkey when registering a registration.");
            }

            if (!callback || typeof callback !== "function") {
                throw new Error(
                    "You must specify a callback function when registering a registration."
                );
            }

            if (typeof hotkey === "string") {
                /**
                 * An hotkey string must comply to these rules:
                 *  - all parts are whitelisted
                 *  - single key part comes last
                 *  - each part is separated by the character: "+"
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
            }

            // Add registration
            const token = nextToken++;
            const registration = {
                hotkey: typeof hotkey === "string" ? hotkey.toLowerCase() : hotkey,
                callback,
                activeElement: null,
                allowRepeat: options && options.allowRepeat,
                global: options && options.global,
                capture: options && options.capture,
            };
            registrations.set(token, registration);

            // Due to the way elements are mounted in the DOM by Owl (bottom-to-top),
            // we need to wait the next micro task tick to set the context owner of the registration.
            Promise.resolve().then(() => {
                registration.activeElement = ui.activeElement;
            });

            return token;
        }

        return {
            /**
             * @param {string} hotkey
             * @param {() => void} callback
             * @param {Object} options
             * @param {boolean} [options.allowRepeat=false]
             * @param {boolean} [options.capture=false]
             * @param {boolean} [options.global=false]
             * @returns {() => boolean}
             */
            add(hotkey, callback, options = {}) {
                const token = registerHotkey(hotkey, callback, options);
                return () => registrations.delete(token);
            },
        };
    },
};

registry.category("services").add("hotkey", hotkeyService);
