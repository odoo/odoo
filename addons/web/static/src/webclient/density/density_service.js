// @ts-check
/** @odoo-module native */

import { reactive } from "@odoo/owl";
import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

/** @type {string[]} */
export const DENSITIES = ["default", "compact", "condensed"];

/** @type {Record<string, string>} */
const DENSITY_CLASSES = {
    compact: "o-density-compact",
    condensed: "o-density-condensed",
};

/**
 * @param {string} density
 * @returns {string}
 */
export function nextDensity(density) {
    const index = DENSITIES.indexOf(density);
    return DENSITIES[(index + 1) % DENSITIES.length];
}

class DensityService {
    constructor() {
        this.persistGeneration = 0;
        this.persistPending = Promise.resolve();
        const userDensity = user.settings?.density;
        const initial = DENSITIES.includes(userDensity) ? userDensity : "default";
        this.state = reactive({ density: initial });
        this.persistedDensity = initial;

        if (cookie.get("content_density") !== this.state.density) {
            cookie.set("content_density", this.state.density);
        }
        applyDensityClass(this.state.density);
    }

    get current() {
        return this.state.density;
    }

    /** @param {string} density */
    _apply(density) {
        this.state.density = density;
        applyDensityClass(density);
        cookie.set("content_density", density);
    }

    /** @param {string} density */
    async set(density) {
        if (!DENSITIES.includes(density)) {
            return;
        }
        const generation = ++this.persistGeneration;
        this._apply(density);
        const persist = async () => {
            try {
                await user.setUserSettings("density", density);
                this.persistedDensity = density;
            } catch (error) {
                if (generation === this.persistGeneration) {
                    this._apply(this.persistedDensity);
                }
                console.warn("Could not persist the content density", error);
            }
        };
        this.persistPending = this.persistPending.then(persist);
        await this.persistPending;
    }

    async cycle() {
        await this.set(nextDensity(this.state.density));
    }
}

export const densityService = {
    /** @returns {DensityService} */
    start() {
        return new DensityService();
    },
};

/** @param {string} density */
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
