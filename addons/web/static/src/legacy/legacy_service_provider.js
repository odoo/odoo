/** @odoo-module **/

import { bus } from "web.core";
import Context from "web.Context";

import { browser } from "../core/browser/browser";
import { registry } from "../core/registry";
import { mapDoActionOptionAPI } from "./backend_utils";

export const legacyServiceProvider = {
    dependencies: ["effect", "action"],
    start({ services }) {
        browser.addEventListener("show-effect", (ev) => {
            services.effect.add(ev.detail);
        });
        bus.on("show-effect", this, (payload) => {
            services.effect.add(payload);
        });

        browser.addEventListener("do-action", (ev) => {
            const payload = ev.detail;
            if (payload.action.context) {
                payload.action.context = new Context(payload.action.context).eval();
            }
            const legacyOptions = mapDoActionOptionAPI(payload.options);
            services.action.doAction(payload.action, legacyOptions);
        });
    },
};

registry.category("services").add("legacy_service_provider", legacyServiceProvider);
