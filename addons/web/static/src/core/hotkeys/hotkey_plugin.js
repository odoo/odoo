import { registry } from "../registry";
import { browser } from "../browser/browser";
import { getVisibleElements } from "../utils/ui";
import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { AUTHORIZED_KEYS, getActiveHotkey, MODIFIERS } from "./hotkey_utils";

/**
 * @typedef {(context: { area: HTMLElement, target: EventTarget }) => void} HotkeyCallback
 *
 * @typedef {Object} HotkeyOptions
 * @property {boolean} [allowRepeat]
 *  allow registration to perform multiple times when hotkey is held down
 * @property {boolean} [bypassEditableProtection]
 *  if true the hotkey service will call this registration
 *  even if an editable element is focused
 * @property {boolean} [global]
 *  allow registration to perform no matter the UI active element
 * @property {() => HTMLElement} [area]
 *  adds a restricted operating area for this hotkey
 * @property {(target: HTMLElement) => boolean} [isAvailable]
 *  adds a validation before calling the hotkey registration's callback
 * @property {() => HTMLElement} [withOverlay]
 *  provides the element on which the overlay should be displayed
 *  Please note that if provided the hotkey will only work with
 *  the overlay access key, similarly to all [data-hotkey] DOM attributes.
 *
 * @typedef {HotkeyOptions & {
 *  hotkey: string,
 *  callback: HotkeyCallback,
 *  activeElement: HTMLElement,
 * }} HotkeyRegistration
 */

export class HotkeyPlugin extends Plugin {
    /** @private */
    ui = usePlugin(UIPlugin);
    /** @private @type {Map<number, HotkeyRegistration>} */
    registrations = new Map();
    /** @private */
    nextToken = 0;
    /** @private */
    overlaysVisible = false;
    // Be aware that all odoo hotkeys are designed with this modifier in mind, so
    // changing the overlay modifier may conflict with some shortcuts.
    overlayModifier = "alt";
    /** @private @type {[EventTarget, string, Function][]} */
    listeners = [];

    setup() {
        this.addListeners(browser);
        onWillDestroy(() => this.removeListeners());
    }

    /** @private */
    addListeners(target) {
        this.addListener(target, "keydown", this.onKeydown);
        this.addListener(target, "keyup", this.removeHotkeyOverlays);
        this.addListener(target, "blur", this.removeHotkeyOverlays);
        this.addListener(target, "click", this.removeHotkeyOverlays);
    }

    /** @private */
    addListener(target, type, listener) {
        target.addEventListener(type, listener);
        this.listeners.push([target, type, listener]);
    }

    /** @private */
    removeListeners() {
        for (const [target, type, listener] of this.listeners) {
            target.removeEventListener(type, listener);
        }
        this.listeners = [];
    }

    /**
     * Handler for keydown events.
     * Verifies if the keyboard event can be dispatched or not.
     * Rules sequence to forbid dispatching :
     * - UI is blocked
     * - the pressed key is not whitelisted
     *
     * @param {KeyboardEvent} event
     * @private
     */
    onKeydown = (event) => {
        if (event.code && event.code.indexOf("Numpad") === 0 && /^\d$/.test(event.key)) {
            // Ignore all number keys from the Keypad because of a certain input method
            // of (advance-)ASCII characters on Windows OS: ALT+[numerical code from keypad]
            // See https://support.microsoft.com/en-us/office/insert-ascii-or-unicode-latin-based-symbols-and-characters-d13f58d3-7bcb-44a7-a4d5-972ee12e50e0#bm1
            return;
        }

        const hotkey = getActiveHotkey(event);
        if (!hotkey) {
            return;
        }
        const activeElement = this.ui.activeElement();
        const isBlocked = this.ui.isBlocked();

        // Do not dispatch if UI is blocked
        if (isBlocked) {
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
        if (!this.overlaysVisible && hotkey === this.overlayModifier) {
            if (this.addHotkeyOverlays(activeElement)) {
                event.preventDefault();
            }
            return;
        }

        // Is the pressed key NOT whitelisted ?
        const singleKey = hotkey.split("+").pop();
        if (!AUTHORIZED_KEYS.includes(singleKey)) {
            return;
        }

        // Protect any editable target that does not explicitly accept hotkeys
        // NB: except for ESC, which is always allowed as hotkey in editables.
        const targetIsEditable =
            event.target instanceof HTMLElement &&
            (/input|textarea/i.test(event.target.tagName) || event.target.isContentEditable) &&
            !event.target.matches("input[type=checkbox], input[type=radio]");
        const shouldProtectEditable =
            targetIsEditable && !event.target.dataset.allowHotkeys && singleKey !== "escape";

        // Finally, prepare and dispatch.
        const infos = {
            activeElement,
            hotkey,
            isRepeated: event.repeat,
            target: event.target,
            shouldProtectEditable,
        };
        const dispatched = this.dispatch(infos);
        if (dispatched) {
            // Only if event has been handled.
            // Purpose: prevent browser defaults
            event.preventDefault();
            // Purpose: stop other window keydown listeners (e.g. home menu)
            event.stopImmediatePropagation();
        }

        // Finally, always remove overlays at that point
        if (this.overlaysVisible) {
            this.removeHotkeyOverlays();
            event.preventDefault();
        }
    };

    /**
     * Dispatches an hotkey to first matching registration.
     * Registrations are iterated in following order:
     * - priority to all registrations done through the hotkeyService.add()
     *   method (NB: in descending order of insertion = newer first)
     * - then all registrations done through the DOM [data-hotkey] attribute
     *
     * @param {{
     *  activeElement: HTMLElement,
     *  hotkey: string,
     *  isRepeated: boolean,
     *  target: EventTarget,
     *  shouldProtectEditable: boolean,
     * }} infos
     * @returns {boolean} true if has been dispatched
     * @private
     */
    dispatch(infos) {
        const { activeElement, hotkey, isRepeated, target, shouldProtectEditable } = infos;

        // Prepare registrations and the common filter
        const reversedRegistrations = Array.from(this.registrations.values()).reverse();
        const domRegistrations = this.getDomRegistrations(hotkey, activeElement);
        const allRegistrations = reversedRegistrations.concat(domRegistrations);

        // Find all candidates
        const candidates = allRegistrations.filter(
            (reg) =>
                reg.hotkey === hotkey &&
                (reg.allowRepeat || !isRepeated) &&
                (reg.bypassEditableProtection || !shouldProtectEditable) &&
                (reg.global || reg.activeElement === activeElement) &&
                (!reg.isAvailable || reg.isAvailable(target)) &&
                (!reg.area || (target && reg.area() && reg.area().contains(target)))
        );

        // First candidate
        let winner = candidates.shift();
        if (winner && winner.area) {
            // If there is an area, find the closest one
            for (const candidate of candidates.filter((c) => Boolean(c.area))) {
                if (candidate.area() && winner.area().contains(candidate.area())) {
                    winner = candidate;
                }
            }
        }

        // Dispatch actual hotkey to the matching registration
        if (winner) {
            winner.callback({
                area: winner.area && winner.area(),
                target,
            });
            return true;
        }
        return false;
    }

    /**
     * Get a list of registrations from the [data-hotkey] defined in the DOM
     *
     * @param {string} hotkey
     * @param {HTMLElement} activeElement
     * @returns {HotkeyRegistration[]}
     * @private
     */
    getDomRegistrations(hotkey, activeElement) {
        const overlayModParts = this.overlayModifier.split("+");
        if (!overlayModParts.every((el) => hotkey.includes(el))) {
            return [];
        }

        // Get all elements having a data-hotkey attribute  and matching
        // the actual hotkey without the overlayModifier.
        const cleanHotkey = hotkey
            .split("+")
            .filter((key) => !overlayModParts.includes(key))
            .join("+");
        const elems = getVisibleElements(activeElement, `[data-hotkey='${cleanHotkey}' i]`);
        return elems.map((el) => ({
            hotkey,
            activeElement,
            bypassEditableProtection: true,
            callback: () => {
                if (document.activeElement) {
                    document.activeElement.blur();
                }
                el.focus();
                setTimeout(() => el.click());
            },
        }));
    }

    /**
     * Add the hotkey overlays respecting the ui active element.
     * @param {HTMLElement} activeElement
     * @returns {boolean} true if overlays were actually displayed
     * @private
     */
    addHotkeyOverlays(activeElement) {
        // Gather the hotkeys to overlay registered through the useHotkey hook.
        const hotkeysFromHookToHighlight = [];
        for (const [, registration] of this.registrations) {
            const overlayElement = registration.withOverlay?.();
            if (overlayElement) {
                hotkeysFromHookToHighlight.push({
                    hotkey: registration.hotkey.replace(`${this.overlayModifier}+`, ""),
                    el: overlayElement,
                });
            }
        }

        // Gather the hotkeys to overlay registered through the DOM datasets.
        const hotkeysFromDomToHighlight = getVisibleElements(
            activeElement,
            "[data-hotkey]:not(:disabled)"
        ).map((el) => ({ hotkey: el.dataset.hotkey, el }));

        const items = [...hotkeysFromDomToHighlight, ...hotkeysFromHookToHighlight];
        if (!items.length) {
            return false;
        }
        for (const item of items) {
            const hotkey = item.hotkey;
            const overlay = document.createElement("div");
            overlay.classList.add(
                "o_web_hotkey_overlay",
                "position-absolute",
                "top-0",
                "bottom-0",
                "start-0",
                "end-0",
                "d-flex",
                "justify-content-center",
                "align-items-center",
                "m-0",
                "bg-black-50",
                "h6"
            );
            // Bootstrap raises the z-index of focused/active buttons inside a
            // btn-group up to 2, which would hide the overlay behind them.
            overlay.style.zIndex = 3;
            const overlayKbd = document.createElement("kbd");
            overlayKbd.className = "small";
            overlayKbd.appendChild(document.createTextNode(hotkey.toUpperCase()));
            overlay.appendChild(overlayKbd);

            let overlayParent;
            if (item.el.tagName.toUpperCase() === "INPUT") {
                // special case for the search input that has an access key
                // defined. We cannot set the overlay on the input itself,
                // only on its parent.
                overlayParent = item.el.parentElement;
            } else {
                overlayParent = item.el;
            }

            if (overlayParent.style.position !== "absolute") {
                overlayParent.style.position = "relative";
            }
            overlayParent.appendChild(overlay);
        }
        this.overlaysVisible = true;
        return true;
    }

    /**
     * Remove all the hotkey overlays.
     * @private
     */
    removeHotkeyOverlays = () => {
        for (const overlay of document.querySelectorAll(".o_web_hotkey_overlay")) {
            overlay.remove();
        }
        this.overlaysVisible = false;
    };

    /**
     * Registers a new hotkey.
     *
     * @param {string} hotkey
     * @param {HotkeyCallback} callback
     * @param {HotkeyOptions} [options]
     * @returns {number} registration token
     * @private
     */
    registerHotkey(hotkey, callback, options = {}) {
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
            .filter((k) => !MODIFIERS.includes(k));
        if (keys.some((k) => !AUTHORIZED_KEYS.includes(k))) {
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
        const token = this.nextToken++;
        /** @type {HotkeyRegistration} */
        const registration = {
            hotkey: hotkey.toLowerCase(),
            callback,
            activeElement: null,
            allowRepeat: options && options.allowRepeat,
            bypassEditableProtection: options && options.bypassEditableProtection,
            global: options && options.global,
            area: options && options.area,
            isAvailable: options && options.isAvailable,
            withOverlay: options && options.withOverlay,
        };

        // Due to the way elements are mounted in the DOM by Owl (bottom-to-top),
        // we need to wait the next micro task tick to set the context owner of the registration.
        Promise.resolve().then(() => {
            registration.activeElement = this.ui.activeElement();
        });

        this.registrations.set(token, registration);
        return token;
    }

    /**
     * Unsubscribes the token corresponding registration.
     *
     * @param {number} token
     * @private
     */
    unregisterHotkey(token) {
        this.registrations.delete(token);
    }

    /**
     * @param {string} hotkey
     * @param {HotkeyCallback} callback
     * @param {HotkeyOptions} [options]
     * @returns {() => void}
     */
    add(hotkey, callback, options = {}) {
        const token = this.registerHotkey(hotkey, callback, options);
        return () => {
            this.unregisterHotkey(token);
        };
    }

    /**
     * @param {HTMLIFrameElement} iframe
     */
    registerIframe(iframe) {
        this.addListeners(iframe.contentWindow);
    }

    /**
     * @param {Window} window
     */
    registerWindow(window) {
        this.addListeners(window);
    }
}

services.add(HotkeyPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the hotkey service are removed
 * -----------------------------------------------------------------------------
 */
export const hotkeyService = {
    dependencies: ["ui"],
    start() {
        return usePlugin(HotkeyPlugin);
    },
};

registry.category("services").add("hotkey", hotkeyService);
/** @typedef {ReturnType<hotkeyService["start"]>} HotkeyService */
