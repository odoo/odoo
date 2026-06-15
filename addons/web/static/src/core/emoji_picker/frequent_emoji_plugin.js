import { registry } from "@web/core/registry";
import { computed, plugin, Plugin, signal, useListener } from "@odoo/owl";
import { services } from "@web/core/services";

const STORAGE_KEY = "web.emoji.frequent";

export class FrequentEmojiPlugin extends Plugin {
    all = signal.Object(JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"));
    mostFrequent = computed(() => {
        return Object.entries(this.all())
            .sort(([, usage_1], [, usage_2]) => usage_2 - usage_1)
            .map(([codepoints]) => codepoints);
    });

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
     * @param {string} codepoints
     */
    incrementEmojiUsage(codepoints) {
        this.all()[codepoints] ||= 0;
        this.all()[codepoints]++;

        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.all()));
    }
}

services.add(FrequentEmojiPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the frequent_emoji service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("frequent_emoji", {
    start() {
        return plugin(FrequentEmojiPlugin);
    }
});
