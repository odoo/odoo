import { onWillStart, Plugin, usePlugin, whenReady } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";
import { session } from "@web/session";
import { TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY, tourRecorderState } from "./tour_recorder_state";

export class TourRecorderPlugin extends Plugin {
    overlay = usePlugin(OverlayPlugin);
    removeTourRecorder = () => {};

    setup() {
        onWillStart(() => this.bootstrap());
    }

    async bootstrap() {
        await whenReady();
        if (
            !window.frameElement &&
            browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY) &&
            !session.is_public
        ) {
            await this.addTourRecorderToOverlay();
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
