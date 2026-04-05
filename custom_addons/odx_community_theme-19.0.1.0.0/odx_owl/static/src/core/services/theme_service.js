/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

const STORAGE_KEY = "odx_owl.theme";
const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

function getStoredTheme() {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return ["light", "dark", "system"].includes(value) ? value : "system";
}

function resolveTheme(theme) {
    if (theme === "system") {
        return mediaQuery.matches ? "dark" : "light";
    }
    return theme;
}

function applyTheme(state) {
    const resolved = resolveTheme(state.theme);
    state.resolvedTheme = resolved;
    document.documentElement.dataset.odxTheme = resolved;
    document.documentElement.style.colorScheme = resolved;
}

export const odxThemeService = {
    start() {
        const state = reactive({
            theme: getStoredTheme(),
            resolvedTheme: "light",
            setTheme(theme) {
                state.theme = ["light", "dark", "system"].includes(theme) ? theme : "system";
                window.localStorage.setItem(STORAGE_KEY, state.theme);
                applyTheme(state);
            },
            toggleTheme() {
                const next = state.resolvedTheme === "dark" ? "light" : "dark";
                state.setTheme(next);
            },
        });

        mediaQuery.addEventListener("change", () => {
            if (state.theme === "system") {
                applyTheme(state);
            }
        });

        applyTheme(state);
        return state;
    },
};

registry.category("services").add("odx_theme", odxThemeService);
