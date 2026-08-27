import { Plugin, usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import {
    tourRecorderState,
    TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY,
} from "@web_tour/tour_recorder/tour_recorder_state";

export class TourRecorderPlugin extends Plugin {
    overlay = usePlugin(OverlayPlugin);
    removeTourRecorder = () => {};

    setup() {
        if (
            browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY) &&
            !session.is_public
        ) {
            this.addTourRecorderToOverlay();
        }
    }

    /**
     * Add tour recorder component in overlay container.
     */
    async addTourRecorderToOverlay() {
        if (!odoo.loader.modules.get("@web_tour/tour_recorder/tour_recorder")) {
            await loadBundle("web_tour.recorder");
        }
        const { TourRecorder } = odoo.loader.modules.get("@web_tour/tour_recorder/tour_recorder");
        const remove = this.overlay.add(
            TourRecorder,
            {
                onClose: () => {
                    remove();
                    browser.localStorage.removeItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY);
                    tourRecorderState.clear();
                },
            },
            { sequence: 99999 }
        );

        this.removeTourRecorder = () => {
            remove();
            browser.localStorage.removeItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY);
            tourRecorderState.clear();
        };
    }

    async startTourRecorder() {
        if (!browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY)) {
            await this.addTourRecorderToOverlay();
        }
        browser.localStorage.setItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY, "1");
    }
}

services.add(TourRecorderPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the tour_recorder_service service are removed
 * -----------------------------------------------------------------------------
 */
export const tourRecorderService = {
    dependencies: ["overlay"],
    start() {
        return usePlugin(TourRecorderPlugin);
    },
};

registry.category("services").add("tour_recorder_service", tourRecorderService);

registry.category("command_provider").add("tour_recorder", {
    provide: (env, options) => {
        const tourRecorder = useService("tour_recorder_service");
        const result = [];
        if (options.searchValue.toLowerCase() === "record") {
            result.push({
                action() {
                    tourRecorder.startTourRecorder();
                },
                name: _t("Enable the tour recorder"),
            });
        }
        return result;
    },
});
