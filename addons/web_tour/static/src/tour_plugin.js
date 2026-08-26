import { onWillStart, Plugin, t, usePlugin, whenReady } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { session } from "@web/session";
import { redirect } from "@web/core/utils/urls";
import { useEnv } from "@web/owl2/utils";
import { tourState } from "@web_tour/tour_state";
import { tourSchema } from "@web_tour/tour_schemas";
import { TourAutomaticPlugin } from "@web_tour/tour_automatic/tour_automatic_plugin";
import { TourRecorderPlugin } from "@web_tour/tour_recorder/tour_recorder_plugin";
import { TourInteractivePlugin } from "@web_tour/tour_interactive/tour_interactive_plugin";

const tourRegistry = registry.category("web_tour.tours");
tourRegistry.addValidation(t.strictObject(tourSchema));

export class TourPlugin extends Plugin {
    env = useEnv();
    orm = usePlugin(ORM);
    automatic = usePlugin(TourAutomaticPlugin);
    interactive = usePlugin(TourInteractivePlugin);
    recorder = usePlugin(TourRecorderPlugin);

    setup() {
        onWillStart(() => this.bootstrap());
    }

    async bootstrap() {
        await whenReady();

        if (window.frameElement) {
            return;
        }

        const paramsTourName = new URLSearchParams(browser.location.search).get("tour");
        if (paramsTourName) {
            this.startTour(paramsTourName, { mode: "manual" });
        }

        if (tourState.getCurrentTour()) {
            const currentConfig = tourState.getCurrentConfig();
            if (
                currentConfig.mode === "auto" ||
                currentConfig.robot ||
                this.interactive.toursEnabled
            ) {
                this.resumeTour();
            } else {
                tourState.clear();
            }
        } else if (session.current_tour) {
            this.startTour(session.current_tour.name, {
                mode: "manual",
                redirect: false,
                rainbowManMessage: session.current_tour.rainbowManMessage,
            });
        }
    }

    /**
     * Check that the registry contains the tour (only for automatic tour)
     * @param {string} name The name of the tour
     */
    isTourReady(name) {
        return tourRegistry.contains(name);
    }

    async resumeTour() {
        const tourName = tourState.getCurrentTour();
        const tourConfig = tourState.getCurrentConfig();
        const tour =
            tourConfig.mode === "auto"
                ? await this.automatic.getTour(tourName)
                : await this.interactive.getTour(tourName);
        if (!tour || !tour.steps.length) {
            tourState.clear();
            return;
        }

        if (tourConfig.mode === "auto") {
            tour.steps.forEach((step) => this.automatic.validateStep(step, tourConfig.debug));
            this.automatic.play(tour);
        } else {
            tour.steps.forEach((step) => this.interactive.validateStep(step, tourConfig.debug));
            await this.interactive.play(tour, tourConfig, async () => {
                const nextTour = await this.orm.call("web_tour.tour", "consume", [tour.name]);
                if (nextTour) {
                    this.startTour(nextTour.name, {
                        mode: "manual",
                        redirect: false,
                        rainbowManMessage: nextTour.rainbowManMessage,
                    });
                }
            });
        }
    }

    /**
     * Starts manual or automatic tour.
     * @param {string} name - The name of the tour to start.
     * @param {Object} [options={}] - Options to customize the tour start.
     * @param {string} [options.url] - URL to start the tour.
     * @param {"auto"|"manual"} [options.mode="auto"] - Tour start mode ("auto" or "manual").
     * @param {number} [options.stepDelay=0] - Delay between each tour step.
     * @param {number} [options.showPointerDuration=0] - Duration to show the pointer on each step.
     * @param {boolean} [options.debug=false] - Enables debug mode for the tour.
     * @param {boolean} [options.redirect=true] - Whether to redirect to `tour.url` if necessary.
     * @param {boolean} [options.robot=false] - In "manual" mode, performs each step's action
     * automatically (using the same helpers as automatic tours) instead of waiting for a real
     * user interaction, while still resolving and displaying the tour pointer as it would for a
     * human. Useful to test that onboarding tours' pointer resolves correctly.
     */
    async startTour(name, options = {}) {
        this.interactive.removePointer();
        this.recorder.removeTourRecorder();

        if (
            !session.is_public &&
            !this.interactive.toursEnabled &&
            options.mode === "manual" &&
            !options.robot
        ) {
            this.interactive.toursEnabled = await this.orm.call(
                "res.users",
                "switch_tour_enabled",
                [!this.interactive.toursEnabled]
            );
        }

        const tourConfig = {
            stepDelay: 0,
            mode: "auto",
            showPointerDuration: 0,
            debug: false,
            redirect: true,
            robot: false,
            ...options,
        };

        tourState.setCurrentConfig(tourConfig);
        tourState.setCurrentTour(name);
        tourState.setCurrentIndex(0);

        if (tourConfig.url && tourConfig.redirect) {
            redirect(tourConfig.url);
        } else {
            await this.resumeTour();
        }
    }
}

services.add(TourPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the tour_service service are removed
 * -----------------------------------------------------------------------------
 */
export const tourService = {
    // localization dependency to make sure translations used by tours are loaded
    dependencies: ["localization"],
    start() {
        const service = usePlugin(TourPlugin);
        odoo.startTour = service.startTour.bind(service);
        odoo.isTourReady = service.isTourReady.bind(service);
        return service;
    },
};

registry.category("services").add("tour_service", tourService);
