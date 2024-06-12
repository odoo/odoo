/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import ToursDialog from "@web_tour/debug/tour_dialog_component";
import { tourState } from "../tour_service/tour_state";

export function disableTours({ env }) {
    if (!env.services.user.isSystem) {
        return null;
    }
    const activeTourNames = tourState.getActiveTourNames();
    if (activeTourNames.length === 0) {
        return null;
    }
    return {
        type: "item",
        description: _t("Disable Tours"),
        callback: async () => {
            await env.services.orm.call("web_tour.tour", "consume", [activeTourNames]);
            for (const tourName of activeTourNames) {
                tourState.clear(tourName);
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
        description: _t("Start Tour"),
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
