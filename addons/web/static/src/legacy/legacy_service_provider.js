/** @odoo-module **/

import { bus } from "@web/legacy/js/services/core";

import { browser } from "../core/browser/browser";
import { registry } from "../core/registry";

export const legacyServiceProvider = {
    dependencies: ["effect", "action"],
    start({ services }) {
        browser.addEventListener("show-effect", (ev) => {
            services.effect.add(ev.detail);
        });
        bus.on("show-effect", this, (payload) => {
            services.effect.add(payload);
        });
    },
};

registry.category("services").add("legacy_service_provider", legacyServiceProvider);
