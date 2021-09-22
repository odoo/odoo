/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import ToursDialog from "@web_tour/debug/tour_dialog_component";
import utils from "web_tour.utils";

export function disableTours({ env }) {
    if (!env.services.user.isSystem) {
        return null;
    }
    const activeTours = env.services.tour.getActiveTours();
    if (activeTours.length === 0) {
        return null;
    }
    return {
        type: "item",
        description: env._t("Disable Tours"),
        callback: async () => {
            const tourNames = activeTours.map(tour => tour.name);
            await env.services.orm.call("web_tour.tour", "consume", [tourNames]);
            for (const tourName of tourNames) {
                browser.localStorage.removeItem(utils.get_debugging_key(tourName));
            }
            browser.location.reload();
        },
        sequence: 50,
    };
}

export function startTour({ env }) {
    if (!env.services.user.isSystem) {
        return null;
    }
    return {
        type: "item",
        description: env._t("Start Tour"),
        callback: async () => {
            env.services.dialog.add(ToursDialog);
        },
        sequence: 60,
    };
}

registry
    .category("debug")
    .category("default")
    .add("web_tour.startTour", startTour)
    .add("web_tour.disableTours", disableTours);
