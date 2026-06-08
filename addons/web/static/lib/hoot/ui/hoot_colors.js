/** @odoo-module */

import { effect, signal, types as t } from "@odoo/owl";
import { getAllColors, getPreferredColorScheme } from "../../hoot-dom/hoot_dom_utils";
import { STORAGE, storageGet, storageSet } from "../hoot_utils";

/**
 * @typedef {"dark" | "light"} ColorScheme
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { entries: $entries, keys: $keys },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/** @type {ColorScheme[]} */
const COLOR_SCHEMES = $keys(getAllColors()).filter((key) => key !== "default");

/** @type {ColorScheme} */
let defaultScheme = storageGet(STORAGE.scheme);
if (!COLOR_SCHEMES.includes(defaultScheme)) {
    defaultScheme = getPreferredColorScheme();
    storageSet(STORAGE.scheme, defaultScheme);
}

const colorChangedCallbacks = [
    () => {
        const { classList } = colorRoot();
        classList.remove(...COLOR_SCHEMES);
        classList.add(colorScheme());
    },
];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function generateStyleSheets() {
    /** @type {Record<string, string>} */
    const styles = {};
    for (const [scheme, values] of $entries(getAllColors())) {
        const content = [];
        for (const [key, value] of $entries(values)) {
            content.push(`--${key}:${value};`);
        }
        styles[scheme] = content.join("");
    }
    return styles;
}

/**
 * @param {(scheme: ColorScheme) => any} callback
 */
export function onColorSchemeChange(callback) {
    colorChangedCallbacks.push(callback);
}

export function toggleColorScheme() {
    colorScheme.set(COLOR_SCHEMES.at(COLOR_SCHEMES.indexOf(colorScheme()) - 1));
    storageSet(STORAGE.scheme, colorScheme());
}

export const colorRoot = signal(null, { type: t.ref(HTMLElement) });
export const colorScheme = signal(defaultScheme, { type: t.selection(["dark", "light"]) });

effect(() => {
    if (!colorRoot()) {
        return;
    }
    for (const callback of colorChangedCallbacks) {
        callback(colorScheme());
    }
});
