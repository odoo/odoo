import { computed, usePlugin, Plugin, signal, useEffect } from "@odoo/owl";
import { services } from "@web/core/services";
import { registry } from "@web/core/registry";

export class TitlePlugin extends Plugin {
    prefix = signal("");
    #titleParts = signal.Object({});
    #defaultTitle = document.title || "Odoo";

    title = computed(() => {
        const prefix = this.prefix() ? this.prefix() + " " : "";
        const name = Object.values(this.#titleParts()).join(" - ") || this.#defaultTitle;
        return prefix + name;
    });

    setup() {
        useEffect(() => {
            document.title = this.title();
        });
    }

    /**
     * @returns {Object<string, string>} a copy of the parts that compose the
     *  document title
     */
    getParts() {
        return Object.assign({}, this.#titleParts());
    }

    /**
     * Update the parts that compose the document title. Each entry's value
     * replaces (or, if falsy, removes) the part stored under its key.
     *
     * @param {Object<string, string>} parts mapping of part keys to their
     *  string values
     */
    setParts(parts) {
        const titleParts = this.#titleParts();
        for (const key in parts) {
            const val = parts[key];
            if (!val) {
                delete titleParts[key];
            } else {
                titleParts[key] = val;
            }
        }
    }
}

services.add(TitlePlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of title services are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("title", {
    start() {
        const titlePlugin = usePlugin(TitlePlugin);
        const titleService = Object.create(titlePlugin);
        Object.defineProperty(titleService, "current", {
            get() {
                return titlePlugin.title();
            },
        });
        titleService.setCounters = function (counters) {
            for (const key in counters) {
                const val = counters[key];
                if (val) {
                    titlePlugin.prefix.set(`(${val})`);
                } else {
                    titlePlugin.prefix.set("");
                }
            }
        };
        titleService.getParts = titlePlugin.getParts.bind(titlePlugin);
        titleService.setParts = titlePlugin.setParts.bind(titlePlugin);
        return titleService;
    },
});
