import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { TourRecorder } from "@web_tour_recorder/tour_recorder/tour_recorder";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {import("@web_tour/tour_service/tour_service").TourStep} TourStep
 *
 * @typedef {{
 *  steps: TourStep[];
 *  name: string;
 *  url: string;
 *  test: boolean;
 * }} CustomTour
 */

const CUSTOM_TOURS_LOCAL_STORAGE_KEY = "custom_tours";
const CUSTOM_RUNNING_TOURS_LOCAL_STORAGE_KEY = "custom_running_tours";
export const TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY = "tour_recorder.active";

export const tourRecorderService = {
    dependencies: ["overlay", "tour_service", "notification"],
    start(_env, { overlay, tour_service, notification }) {
        if (browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY)) {
            overlay.add(TourRecorder, {}, { sequence: 99999 });
        }

        tour_service.bus.addEventListener("TOUR-FINISHED", () => {
            browser.localStorage.removeItem(CUSTOM_RUNNING_TOURS_LOCAL_STORAGE_KEY);
        });

        const customRunningTourString = browser.localStorage.getItem(
            CUSTOM_RUNNING_TOURS_LOCAL_STORAGE_KEY
        );
        if (customRunningTourString) {
            const customRunningTour = JSON.parse(customRunningTourString);
            registry.category("web_tour.tours").add(customRunningTour.name, {
                ...customRunningTour,
                steps: () => customRunningTour.steps,
            });
        }

        /**
         * @param {CustomTour} customTour
         * @returns {boolean} The tour has been added successfully
         */
        function addCustomTour(customTour) {
            const customTours = getCustomTours();
            if (customTours.some((t) => t.name === customTour.name)) {
                notification.add(_t("Custom tour '%s' already exist!", customTour.name), {
                    type: "danger",
                });
                return false;
            } else {
                customTours.push(customTour);
                browser.localStorage.setItem(
                    CUSTOM_TOURS_LOCAL_STORAGE_KEY,
                    JSON.stringify(customTours)
                );
                notification.add(_t("Custom tour '%s' has been added.", customTour.name), {
                    type: "success",
                });
                return true;
            }
        }

        /**
         * @param {CustomTour} tour
         */
        function removeCustomTour(tour) {
            let customTours = getCustomTours();
            customTours = customTours.filter((t) => t.name !== tour.name);
            browser.localStorage.setItem(
                CUSTOM_TOURS_LOCAL_STORAGE_KEY,
                JSON.stringify(customTours)
            );
            notification.add(_t("Tour '%s' correctly deleted.", tour.name), {
                type: "success",
            });
        }

        /**
         * @returns {CustomTour[]}
         */
        function getCustomTours() {
            const customToursString = browser.localStorage.getItem(CUSTOM_TOURS_LOCAL_STORAGE_KEY);
            return JSON.parse(customToursString || "[]");
        }

        /**
         * @param {string} customTourName
         */
        function startCustomTour(customTourName, options) {
            const customTours = getCustomTours();
            const customTour = customTours.find((t) => t.name === customTourName);
            if (!registry.category("web_tour.tours").contains(customTour.name)) {
                registry.category("web_tour.tours").add(customTour.name, {
                    ...customTour,
                    steps: () => customTour.steps,
                });
                browser.localStorage.setItem(
                    CUSTOM_RUNNING_TOURS_LOCAL_STORAGE_KEY,
                    JSON.stringify(customTour)
                );
            }
            tour_service.startTour(customTour.name, options);
        }

        return {
            addCustomTour,
            removeCustomTour,
            getCustomTours,
            startCustomTour,
        };
    },
};

registry.category("services").add("tour_recorder", tourRecorderService);
