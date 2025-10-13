import { Component, markup, whenReady, validate } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { loadBundle } from "@web/core/assets";
import { createPointerState } from "@web_tour/js/tour_pointer/tour_pointer_state";
import { tourState } from "@web_tour/js/tour_state";
import { callWithUnloadCheck } from "@web_tour/js/utils/tour_utils";
import {
    tourRecorderState,
    TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY,
} from "@web_tour/js/tour_recorder/tour_recorder_state";
import { redirect } from "@web/core/utils/urls";

class OnboardingItem extends Component {
    static components = { DropdownItem };
    static template = "web_tour.OnboardingItem";
    static props = {
        toursEnabled: { type: Boolean },
        toggleItem: { type: Function },
    };
    setup() {}
}

const stepSchema = {
    id: { type: [String], optional: true },
    content: { type: [String, Object], optional: true }, //allow object(_t && markup)
    debugHelp: { type: String, optional: true },
    isActive: { type: Array, element: String, optional: true },
    run: { type: [String, Function, Boolean], optional: true },
    timeout: {
        optional: true,
        validate(value) {
            return value >= 0 && value <= 60000;
        },
    },
    tooltipPosition: {
        optional: true,
        validate(value) {
            return ["top", "bottom", "left", "right"].includes(value);
        },
    },
    trigger: { type: String },
    expectUnloadPage: { type: Boolean, optional: true },
    //ONLY IN DEBUG MODE
    pause: { type: Boolean, optional: true },
    break: { type: Boolean, optional: true },
};

const tourSchema = {
    name: { type: String, optional: true },
    steps: Function,
    url: { type: String, optional: true },
    wait_for: { type: [Function, Object], optional: true },
};

const tourRegistry = registry.category("web_tour.tours");
tourRegistry.addValidation(tourSchema);

export class TourService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.orm = services["orm"];
        this.effect = services["effect"];
        this.overlay = services["overlay"];
        this.toursEnabled = session?.tour_enabled;
        this.pointer = createPointerState();
        this.pointer.stop = () => {};
        this.addOnboardingItemInDebugMenu();

        if (window.frameElement) {
            return;
        }

        const paramsTourName = new URLSearchParams(browser.location.search).get("tour");
        if (paramsTourName) {
            this.startTour(paramsTourName, { mode: "manual", fromDB: true });
        }

        if (tourState.getCurrentTour()) {
            if (tourState.getCurrentConfig().mode === "auto" || this.toursEnabled) {
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

        if (
            browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY) &&
            !session.is_public
        ) {
            this.addTourRecorderToOverlay();
        }
    }

    addOnboardingItemInDebugMenu() {
        const debugMenuRegistry = registry.category("debug").category("default");
        debugMenuRegistry.add("onboardingItem", () => ({
            type: "component",
            Component: OnboardingItem,
            props: {
                toursEnabled: this.toursEnabled || false,
                toggleItem: async () => {
                    tourState.clear();
                    this.toursEnabled = await this.orm.call("res.users", "switch_tour_enabled", [
                        !this.toursEnabled,
                    ]);
                    browser.location.reload();
                },
            },
            sequence: 500,
            section: "testing",
        }));
    }

    async getTourRecorder() {
        let tourRecorder = odoo.loader.modules.get(
            "@web_tour/js/tour_recorder/tour_recorder"
        ).TourRecorder;
        if (!tourRecorder) {
            await loadBundle("web_tour.recorder");
            tourRecorder = odoo.loader.modules.get(
                "@web_tour/js/tour_recorder/tour_recorder"
            ).TourRecorder;
        }
        return tourRecorder;
    }

    /**
     * Add tour recorder component in overlay container.
     */
    async addTourRecorderToOverlay() {
        const tourRecorder = await this.getTourRecorder();
        const remove = this.overlay.add(
            tourRecorder,
            {
                onClose: () => {
                    remove();
                    browser.localStorage.removeItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY);
                    tourRecorderState.clear();
                },
            },
            { sequence: 99999 }
        );
    }

    /**
     * @param {string} tourName
     */
    async getTourFromDB(tourName) {
        const tour = await this.orm.call("web_tour.tour", "get_tour_json_by_name", [tourName]);
        if (!tour) {
            throw new Error(`Tour '${tourName}' is not found in the database.`);
        }

        if (!tour.steps.length && tourRegistry.contains(tour.name)) {
            tour.steps = tourRegistry.get(tour.name).steps();
        }

        return tour;
    }

    /**
     * @param {string} tourName
     */
    getTourFromRegistry(tourName) {
        if (!tourRegistry.contains(tourName)) {
            return;
        }
        const tour = tourRegistry.get(tourName);
        return {
            ...tour,
            steps: tour.steps(),
            name: tourName,
            waitFor: tour.wait_for || Promise.resolve(),
        };
    }

    /**
     * @param {string} tourName
     */
    async isTourReady(tourName) {
        await this.getTourFromRegistry(tourName).waitFor;
        return true;
    }

    async resumeTour() {
        const tourName = tourState.getCurrentTour();
        const tourConfig = tourState.getCurrentConfig();

        let tour = this.getTourFromRegistry(tourName);
        if (tourConfig.fromDB) {
            tour = await this.getTourFromDB(tourName);
        }
        if (!tour) {
            return;
        }

        tour.steps.forEach((step) => this.validateStep(step));

        if (tourConfig.mode === "auto") {
            if (!odoo.loader.modules.get("@web_tour/js/tour_automatic/tour_automatic")) {
                await loadBundle("web_tour.automatic", { css: false });
            }
            const { TourAutomatic } = odoo.loader.modules.get(
                "@web_tour/js/tour_automatic/tour_automatic"
            );
            new TourAutomatic(tour).start();
        } else {
            await loadBundle("web_tour.interactive");
            const { TourPointer } = odoo.loader.modules.get(
                "@web_tour/js/tour_pointer/tour_pointer"
            );
            this.pointer.stop = this.overlay.add(
                TourPointer,
                {
                    pointerState: this.pointer.state,
                    bounce: !(tourConfig.mode === "auto" && tourConfig.keepWatchBrowser),
                },
                {
                    sequence: 1100, // sequence based on bootstrap z-index values.
                }
            );
            const { TourInteractive } = odoo.loader.modules.get(
                "@web_tour/js/tour_interactive/tour_interactive"
            );
            new TourInteractive(tour).start(this.env, this.pointer, async () => {
                this.pointer.stop();
                tourState.clear();
                browser.console.log("tour succeeded");
                let message = tourConfig.rainbowManMessage || tour.rainbowManMessage;
                if (message) {
                    message = window.DOMPurify.sanitize(tourConfig.rainbowManMessage);
                    this.effect.add({
                        type: "rainbow_man",
                        message: markup(message),
                    });
                }

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
     * This retrieves a tour from the internal registry or from the database
     * if `options.fromDB` is set.
     *
     * @param {string} tourName - The name of the tour to start.
     * @param {Object} [options={}] - Options to customize the tour start.
     * @param {boolean} [options.fromDB=false] - Whether the tour should be loaded from the database.
     * @param {string} [options.url] - URL to start the tour.
     * @param {"auto"|"manual"} [options.mode="auto"] - Tour start mode ("auto" or "manual").
     * @param {number} [options.delayToCheckUndeterminisms=0] - Delay to check for indeterminisms in steps.
     * @param {number} [options.stepDelay=0] - Delay between each tour step.
     * @param {boolean} [options.keepWatchBrowser=false] - Whether to keep watching the browser continuously.
     * @param {number} [options.showPointerDuration=0] - Duration to show the pointer on each step.
     * @param {boolean} [options.debug=false] - Enables debug mode for the tour.
     * @param {boolean} [options.redirect=true] - Whether to redirect to `tour.url` if necessary.
     */
    async startTour(tourName, options = {}) {
        this.pointer.stop();
        const tourFromRegistry = this.getTourFromRegistry(tourName);

        if (!tourFromRegistry && !options.fromDB) {
            // Sometime tours are not loaded depending on the modules.
            // For example, point_of_sale do not load all tours assets.
            return;
        }

        const tour = options.fromDB ? { name: tourName, url: options.url } : tourFromRegistry;
        if (!session.is_public && !this.toursEnabled && options.mode === "manual") {
            this.toursEnabled = await this.orm.call("res.users", "switch_tour_enabled", [
                !this.toursEnabled,
            ]);
        }

        const tourConfig = {
            delayToCheckUndeterminisms: 0,
            stepDelay: 0,
            keepWatchBrowser: false,
            mode: "auto",
            showPointerDuration: 0,
            debug: false,
            redirect: true,
            ...options,
        };

        tourState.setCurrentConfig(tourConfig);
        tourState.setCurrentTour(tour.name);
        tourState.setCurrentIndex(0);

        const willUnload = callWithUnloadCheck(() => {
            if (tour.url && tourConfig.startUrl != tour.url && tourConfig.redirect) {
                redirect(tour.url);
            }
        });
        if (!willUnload) {
            await this.resumeTour();
        }
    }

    async startTourRecorder() {
        if (!browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY)) {
            await this.addTourRecorderToOverlay();
        }
        browser.localStorage.setItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY, "1");
    }

    /**
     * Validate a step according to {@link stepSchema}.
     * @param {Object} step - The step object to validate.
     */
    validateStep(step) {
        try {
            validate(step, stepSchema);
        } catch (error) {
            console.error(
                `Error in schema for TourStep ${JSON.stringify(step, null, 4)}\n${error.message}`
            );
        }
    }
}

registry.category("services").add("tour_service", {
    // localization dependency to make sure translations used by tours are loaded
    dependencies: ["orm", "effect", "overlay", "localization"],
    async start(env, services) {
        await whenReady();
        const service = new TourService(env, services);
        odoo.startTour = service.startTour.bind(service);
        odoo.isTourReady = service.isTourReady.bind(service);

        return service;
    },
});
