/** @odoo-module */

import { reactive, useState } from "@odoo/owl";
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
        const { classList } = current.root;
        classList.remove(...COLOR_SCHEMES);
        classList.add(current.scheme);
    },
];
const current = reactive(
    {
        /** @type {HTMLElement | null} */
        root: null,
        scheme: defaultScheme,
    },
    () => {
        if (!current.root) {
            return;
        }
        for (const callback of colorChangedCallbacks) {
            callback(current.scheme);
        }
    }
);
current.root;

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

export function getColorScheme() {
    return current.scheme;
}

/**
 * @param {(scheme: ColorScheme) => any} callback
 */
export function onColorSchemeChange(callback) {
    colorChangedCallbacks.push(callback);
}

/**
 * @param {HTMLElement | null} element
 */
export function setColorRoot(element) {
    current.root = element;
}

export function toggleColorScheme() {
    current.scheme = COLOR_SCHEMES.at(COLOR_SCHEMES.indexOf(current.scheme) - 1);
    storageSet(STORAGE.scheme, current.scheme);
}

export function useColorScheme() {
    return useState(current);
}
