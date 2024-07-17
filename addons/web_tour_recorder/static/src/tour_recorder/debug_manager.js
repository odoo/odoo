/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import {
    CUSTOM_RUNNING_TOURS_LOCAL_STORAGE_KEY,
    TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY,
} from "@web_tour_recorder/tour_recorder/tour_recorder_service";
import { user } from "@web/core/user";
import { disableTours } from "@web_tour/debug/debug_manager";

function disableToursAndCustom({ env }) {
    const disableTourMenuItem = disableTours({ env });

    if (!disableTourMenuItem) {
        return null;
    } else {
        return {
            ...disableTourMenuItem,
            callback: async () => {
                browser.localStorage.removeItem(CUSTOM_RUNNING_TOURS_LOCAL_STORAGE_KEY);
                await disableTourMenuItem.callback();
            },
        };
    }
}

function tourRecorder() {
    if (!user.isSystem) {
        return null;
    }

    if (!browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY)) {
        return {
            type: "item",
            description: _t("Start Tour Recorder"),
            callback: () => {
                browser.localStorage.setItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY, "1");
                browser.location.reload();
            },
            sequence: 70,
        };
    } else {
        return {
            type: "item",
            description: _t("Disable Tour Recorder"),
            callback: () => {
                browser.localStorage.removeItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY);
                browser.location.reload();
            },
            sequence: 80,
        };
    }
}

registry.category("debug").category("default").add("web_tour_recorder.tour_recorder", tourRecorder);

registry.category("debug").category("default").remove("web_tour.disableTours");

registry.category("debug").category("default").add("web_tour.disableTours", disableToursAndCustom);
