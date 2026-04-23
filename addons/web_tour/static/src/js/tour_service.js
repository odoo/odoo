import { Component, markup, whenReady, validate } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { loadBundle } from "@web/core/assets";
import { pointerState } from "@web_tour/js/tour_pointer/tour_pointer";
import { tourState } from "@web_tour/js/tour_state";
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
        this.removePointer = () => {};
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

    /**
     * Add tour recorder component in overlay container.
     */
    async addTourRecorderToOverlay() {
        if (!odoo.loader.modules.get("@web_tour/js/tour_recorder/tour_recorder")) {
            await loadBundle("web_tour.recorder");
        }
        const { TourRecorder } = odoo.loader.modules.get(
            "@web_tour/js/tour_recorder/tour_recorder"
        );
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
    }

    /**
     * @param {string} name The name of the tour
     */
    async getTour(name, options) {
        let tour = tourRegistry.get(name, null);
        if (options.mode === "manual" && options.fromDB) {
            tour = await this.orm.call("web_tour.tour", "get_tour_json_by_name", [name]);
            if (!tour) {
                throw new Error(`Tour '${name}' is not found in the database.`);
            }

            if (!tour.steps.length && tourRegistry.contains(tour.name)) {
                tour.steps = tourRegistry.get(tour.name).steps;
            }
        }
        if (!tour) {
            return undefined;
        }
        const url = options.fromDB ? options.url : tour.url;
        return {
            ...tour,
            name,
            url,
            steps:
                typeof tour.steps === "function"
                    ? tour.steps()
                    : Array.isArray(tour.steps)
                    ? tour.steps
                    : [],
            waitFor: tour.wait_for || Promise.resolve(),
        };
    }

    /**
     * Wait the tour is ready (only for automatic tour)
     * @param {string} name The name of the tour
     */
    async isTourReady(name) {
        if (!tourRegistry.contains(name)) {
            return false;
        }
        const tour = tourRegistry.get(name);
        await (tour.wait_for || Promise.resolve());
        return true;
    }

    async resumeTour() {
        const tourName = tourState.getCurrentTour();
        const tourConfig = tourState.getCurrentConfig();
        const tour = await this.getTour(tourName, tourConfig);
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
            this.removePointer = this.overlay.add(
                TourPointer,
                {
                    pointerState,
                    bounce: !(tourConfig.mode === "auto" && tourConfig.keepWatchBrowser),
                },
                {
                    sequence: 1100, // sequence based on bootstrap z-index values.
                }
            );
            const { TourInteractive } = odoo.loader.modules.get(
                "@web_tour/js/tour_interactive/tour_interactive"
            );
            new TourInteractive(tour).start(this.env, async () => {
                this.removePointer();
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
     * @param {string} name - The name of the tour to start.
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
    async startTour(name, options = {}) {
        this.removePointer();
        const tour = await this.getTour(name, options);
        if (!tour) {
            return;
        }
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
        tourState.setCurrentTour(name);
        tourState.setCurrentIndex(0);

        if (tour.url && tourConfig.startUrl != tour.url && tourConfig.redirect) {
            redirect(tour.url);
        } else {
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
