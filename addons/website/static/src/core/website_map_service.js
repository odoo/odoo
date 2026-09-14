/** @odoo-module native */
import { registry } from "@web/core/registry";
import { createGoogleMapsService } from "@website/utils/google_maps";

export const websiteMapService = {
    dependencies: ["public.interactions", "notification"],
    start(env, deps) {
        const publicInteractions = deps["public.interactions"];
        return createGoogleMapsService(deps.notification, () => {
            for (const el of document.querySelectorAll("section.s_google_map")) {
                publicInteractions.stopInteractions(el);
                publicInteractions.startInteractions(el);
            }
        });
    },
};

registry.category("services").add("website_map", websiteMapService);
