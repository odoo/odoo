import { computed, Plugin, signal, useListener } from "@odoo/owl";
import { services } from "@web/core/services";

const STORAGE_KEY = "html_editor.icon.frequent";

/**
 * Counts how many times each icon was picked, to list the most frequently
 * used ones first in the icon picker. Shared by the browser tabs through the
 * local storage, like the frequent emojis.
 */
export class FrequentIconPlugin extends Plugin {
    all = signal.Object(JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"));
    mostFrequent = computed(() =>
        Object.entries(this.all())
            .sort(([, usage_1], [, usage_2]) => usage_2 - usage_1)
            .map(([iconId]) => iconId)
    );

    setup() {
        useListener(window, "storage", (ev) => {
            if (ev.key === STORAGE_KEY) {
                this.all.set(ev.newValue ? JSON.parse(ev.newValue) : {});
            } else if (ev.key === null) {
                this.all.set({});
            }
        });
    }

    /**
     * @param {string} iconId
     */
    incrementIconUsage(iconId) {
        this.all()[iconId] ||= 0;
        this.all()[iconId]++;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.all()));
    }
}

services.add(FrequentIconPlugin);
