/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY } from "@web_tour_recorder/tour_recorder/tour_recorder_service";
import { user } from "@web/core/user";

function tourRecorder() {
    if (!user.isSystem) {
        return null;
    }

    if (!browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY)) {
        return {
            type: "item",
            description: _t("Start Tour Recorder"),
            callback: async () => {
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

registry
    .category("debug")
    .category("default")
    .add("web_tour_recorder.tour_recorder", tourRecorder)
