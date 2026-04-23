import { validate } from "@web/owl2/utils";
import { Component, markup, whenReady } from "@odoo/owl";
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
import { _t } from "@web/core/l10n/translation";

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
};

const stepSchemaDebug = {
    ...stepSchema,
    pause: { type: Boolean, optional: true },
    break: { type: Boolean, optional: true },
};

const tourSchema = {
    steps: Function,
    undeterministicTour_doNotCopy: { type: Boolean, optional: true },
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
        this.removeTourRecorder = () => {};
        this.addOnboardingItemInDebugMenu();

        if (window.frameElement) {
            return;
        }

        const paramsTourName = new URLSearchParams(browser.location.search).get("tour");
        if (paramsTourName) {
            this.startTour(paramsTourName, { mode: "manual" });
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

        this.removeTourRecorder = () => {
            remove();
            browser.localStorage.removeItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY);
            tourRecorderState.clear();
        };
    }

    /**
     * @param {string} name The name of the tour
     */
    async getTour(name, options) {
        // Onboarding tour (come from database (.xml files))
        if (options.mode === "manual") {
            const tour = await this.orm.call("web_tour.tour", "get_tour_json_by_name", [name]);
            if (!tour) {
                throw new Error(`Tour '${name}' is not found in the database.`);
            }
            if (!tour.steps.length && tourRegistry.contains(tour.name)) {
                tour.steps = tourRegistry.get(tour.name).steps;
            }
            return {
                ...tour,
                steps:
                    typeof tour.steps === "function"
                        ? tour.steps()
                        : Array.isArray(tour.steps)
                        ? tour.steps
                        : [],
            };
        }
        // Automatic tour (come from registry)
        else {
            await this.waitUntilTourRegistered(name);
            const tour = tourRegistry.get(name, null);
            if (!tour) {
                throw new Error(`Tour '${name}' is not found in registry 'web_tour.tours'.`);
            }
            return {
                ...tour,
                name,
                steps: tour.steps(),
            };
        }
    }

    /**
     * Waits up to 5 seconds for a tour to be registered in the client-side
     * tour registry.
     *
     * This is required because after a browser refresh, the tour definition
     * may not yet be loaded when execution starts. Without this guard,
     * the tour could abort if it is triggered before being registered.
     *
     * @param {string} name - The tour name.
     * @returns {Promise<boolean>} Resolves to `true` if the tour is found
     *   within the timeout, otherwise `false`.
     */
    async waitUntilTourRegistered(name) {
        const start = Date.now();
        while (!tourRegistry.contains(name) && Date.now() - start <= 5000) {
            await new Promise((r) => setTimeout(r, 50));
        }
        return tourRegistry.contains(name);
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
        const tour = await this.getTour(tourName, tourConfig);
        if (!tour || !tour.steps.length) {
            tourState.clear();
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
                if (message && window.DOMPurify) {
                    message = window.DOMPurify.sanitize(message);
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
     * @param {string} name - The name of the tour to start.
     * @param {Object} [options={}] - Options to customize the tour start.
     * @param {string} [options.url] - URL to start the tour.
     * @param {"auto"|"manual"} [options.mode="auto"] - Tour start mode ("auto" or "manual").
     * @param {number} [options.stepDelay=0] - Delay between each tour step.
     * @param {number} [options.showPointerDuration=0] - Duration to show the pointer on each step.
     * @param {boolean} [options.debug=false] - Enables debug mode for the tour.
     * @param {boolean} [options.redirect=true] - Whether to redirect to `tour.url` if necessary.
     */
    async startTour(name, options = {}) {
        this.removePointer();
        this.removeTourRecorder();
        const tour = await this.getTour(name, options);

        if (!session.is_public && !this.toursEnabled && options.mode === "manual") {
            this.toursEnabled = await this.orm.call("res.users", "switch_tour_enabled", [
                !this.toursEnabled,
            ]);
        }

        const tourConfig = {
            stepDelay: 0,
            mode: "auto",
            showPointerDuration: 0,
            debug: false,
            redirect: true,
            allowDelayToRemove: tour.undeterministicTour_doNotCopy,
            ...options,
        };

        tourState.setCurrentConfig(tourConfig);
        tourState.setCurrentTour(name);
        tourState.setCurrentIndex(0);

        if (tourConfig.mode === "manual" && tour.url && tourConfig.redirect) {
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
        const tourConfig = tourState.getCurrentConfig();
        try {
            validate(step, tourConfig.debug ? stepSchemaDebug : stepSchema);
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

registry.category("command_provider").add("tour_recorder", {
    provide: (env, options) => {
        const result = [];
        if (options.searchValue.toLowerCase() === "record") {
            result.push({
                action() {
                    env.services["tour_service"].startTourRecorder();
                },
                name: _t("Enable the tour recorder"),
            });
        }
        return result;
    },
});
