import { isMacOS } from "../browser/feature_detection";
import { range } from "../utils/numbers";

// Kept in their own leaf module (rather than in hotkey_plugin.js) so that
// ui_plugin.js can depend on `getActiveHotkey` without creating an import
// cycle: HotkeyPlugin depends on UIPlugin, so UIPlugin can't depend back on
// hotkey_plugin.js.

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
    "space",
];
const F_KEYS = range(1, 13).map((n) => `f${n}`);

export const MODIFIERS = ["alt", "control", "shift"];
export const AUTHORIZED_KEYS = [
    ...ALPHANUM_KEYS,
    ...NAV_KEYS,
    ...F_KEYS,
    "escape",
    "<",
    ">",
    ".",
    "?",
];

/**
 * Get the actual hotkey being pressed.
 *
 * @param {KeyboardEvent} ev
 * @returns {string} the active hotkey, in lowercase
 */
export function getActiveHotkey(ev) {
    if (!ev.key) {
        // Chrome may trigger incomplete keydown events under certain circumstances.
        // E.g. when using browser built-in autocomplete on an input.
        // See https://stackoverflow.com/questions/59534586/google-chrome-fires-keydown-event-when-form-autocomplete
        return "";
    }
    if (ev.isComposing) {
        // This case happens with an IME for example: we let it handle all key events.
        return "";
    }
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

    // The browser space is natively " ", we want "space" for esthetic reasons
    if (key === " ") {
        key = "space";
    }

    // Identify if the user has tapped on the number keys above the text keys.
    if (ev.code && ev.code.indexOf("Digit") === 0) {
        key = ev.code.slice(-1);
    }
    // Prefer physical keys for non-latin keyboard layout.
    if (!AUTHORIZED_KEYS.includes(key) && ev.code && ev.code.indexOf("Key") === 0) {
        key = ev.code.slice(-1).toLowerCase();
    }
    // Make sure we do not duplicate a modifier key
    if (!MODIFIERS.includes(key)) {
        hotkey.push(key);
    }

    return hotkey.join("+");
}
