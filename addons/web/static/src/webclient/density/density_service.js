// @ts-check

/** @module @web/webclient/density/density_service - Service managing content density (default/compact/condensed) via body CSS class toggles */

import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";
import { user } from "@web/services/user";

/** @type {string[]} */
const VALID_DENSITIES = ["default", "compact", "condensed"];
/** @type {Record<string, string>} */
const DENSITY_CLASSES = {
    compact: "o-density-compact",
    condensed: "o-density-condensed",
};

/**
 * Manage content density (default/compact/condensed) via a body class.
 *
 * Unlike dark mode (which swaps CSS bundles and reloads), density only
 * toggles a body class that overrides CSS custom properties — so switching
 * is instant with no page reload.
 */
export const densityService = {
    /** @returns {{ current: string, set: (density: string) => Promise<void>, cycle: () => Promise<void> }} */
    start() {
        let effectiveDensity = "default";
        const userDensity = user.settings?.density;
        if (VALID_DENSITIES.includes(userDensity)) {
            effectiveDensity = userDensity;
        }

        // Reconcile cookie with user setting
        if (cookie.get("content_density") !== effectiveDensity) {
            cookie.set("content_density", effectiveDensity);
        }

        // Apply body class (may already be set by SSR)
        applyDensityClass(effectiveDensity);

        return {
            get current() {
                return effectiveDensity;
            },
            /** Switch to the given density without page reload. */
            async set(density) {
                if (!VALID_DENSITIES.includes(density)) {
                    return;
                }
                effectiveDensity = density;
                applyDensityClass(density);
                cookie.set("content_density", density);
                await user.setUserSettings("density", density);
            },
            /** Cycle: default → compact → condensed → default. */
            async cycle() {
                const order = ["default", "compact", "condensed"];
                const idx = (order.indexOf(effectiveDensity) + 1) % order.length;
                await this.set(order[idx]);
            },
        };
    },
};

/**
 * Toggle the appropriate body CSS class for the given density.
 * @param {string} density - One of "default", "compact", or "condensed"
 */
function applyDensityClass(density) {
    const { classList } = document.body;
    for (const cls of Object.values(DENSITY_CLASSES)) {
        classList.remove(cls);
    }
    if (density in DENSITY_CLASSES) {
        classList.add(DENSITY_CLASSES[density]);
    }
}

registry.category("services").add("density", densityService);
