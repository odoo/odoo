/** @odoo-module */

import { reactive, useState } from "@odoo/owl";
import { STORAGE, storageGet, storageSet } from "../hoot_utils";

/**
 * @typedef {"dark" | "light"} ColorScheme
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    matchMedia,
    Object: { entries: $entries, keys: $keys },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const GRAYS = {
    100: "#f1f5f9",
    200: "#e2e8f0",
    300: "#cbd5e1",
    400: "#94a3b8",
    500: "#64748b",
    600: "#475569",
    700: "#334155",
    800: "#1e293b",
    900: "#0f172a",
};

/** @type {Record<ColorScheme, Record<string, string>>} */
const COLOR_VALUES = {
    default: {
        // Generic colors
        black: "#000000",
        white: "#ffffff",

        // Grays
        "gray-100": GRAYS[100],
        "gray-200": GRAYS[200],
        "gray-300": GRAYS[300],
        "gray-400": GRAYS[400],
        "gray-500": GRAYS[500],
        "gray-600": GRAYS[600],
        "gray-700": GRAYS[700],
        "gray-800": GRAYS[800],
        "gray-900": GRAYS[900],
    },
    light: {
        // Generic colors
        primary: "#714b67",
        secondary: "#74b4b9",
        abort: "#f59e0b",
        "abort-900": "#fef3c7",
        fail: "#9f1239",
        "fail-900": "#fecdd3",
        pass: "#047857",
        "pass-900": "#ecfdf5",
        skip: "#0891b2",
        "skip-900": "#e0f2fe",
        todo: "#581c87",
        "todo-900": "#f3e8ff",
        muted: GRAYS[400],

        // App colors
        bg: GRAYS[100],
        text: GRAYS[900],
        "status-bg": GRAYS[300],
        "btn-bg": "#714b67",
        "btn-bg-hover": "#624159",
        "btn-text": "#ffffff",
        "bg-result": "rgba(255, 255, 255, 0.6)",
        "border-result": GRAYS[300],
        "border-search": "#d8dadd",
        "shadow-opacity": 0.1,

        // HootReporting colors
        "bg-report": "#ffffff",
        "text-report": "#202124",
        "border-report": "#f0f0f0",
        "bg-report-error": "#fff0f0",
        "text-report-error": "#ff0000",
        "border-report-error": "#ffd6d6",
        "text-report-number": "#1a1aa6",
        "text-report-string": "#c80000",
        "text-report-key": "#881280",
        "text-report-html-tag": "#881280",
        "text-report-html-id": "#1a1aa8",
        "text-report-html-class": "#994500",
    },
    dark: {
        // Generic colors
        primary: "#14b8a6",
        abort: "#fbbf24",
        "abort-900": "#422006",
        fail: "#fb7185",
        "fail-900": "#4c0519",
        pass: "#34d399",
        "pass-900": "#064e3b",
        skip: "#22d3ee",
        "skip-900": "#083344",
        todo: "#a855f7",
        "todo-900": "#3b0764",
        muted: GRAYS[500],

        // App colors
        bg: GRAYS[900],
        text: GRAYS[100],
        "status-bg": GRAYS[700],
        "btn-bg": "#00dac5",
        "btn-bg-hover": "#00c1ae",
        "btn-text": "#000000",
        "bg-result": "rgba(0, 0, 0, 0.5)",
        "border-result": GRAYS[600],
        "border-search": "#3c3f4c",
        "shadow-opacity": 0.4,

        // HootReporting colors
        "bg-report": "#202124",
        "text-report": "#e8eaed",
        "border-report": "#3a3a3a",
        "bg-report-error": "#290000",
        "text-report-error": "#ff8080",
        "border-report-error": "#5c0000",
        "text-report-number": "#9980ff",
        "text-report-string": "#f28b54",
        "text-report-key": "#5db0d7",
        "text-report-html-tag": "#5db0d7",
        "text-report-html-id": "#f29364",
        "text-report-html-class": "#9bbbdc",
    },
};

/** @type {ColorScheme[]} */
const COLOR_SCHEMES = $keys(COLOR_VALUES).filter((k) => k !== "default");

/** @type {ColorScheme} */
let defaultScheme = storageGet(STORAGE.scheme);
if (!COLOR_SCHEMES.includes(defaultScheme)) {
    defaultScheme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
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
            callback();
        }
    }
);
current.root;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function getColors() {
    return COLOR_VALUES[current.scheme];
}

export function generateStyleSheets() {
    /** @type {Record<string, string>} */
    const styles = {};
    for (const [scheme, values] of $entries(COLOR_VALUES)) {
        const content = [];
        for (const [key, value] of $entries(values)) {
            content.push(`--${key}:${value};`);
        }
        styles[scheme] = content.join("");
    }
    return styles;
}

/**
 * @param {() => any} callback
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
