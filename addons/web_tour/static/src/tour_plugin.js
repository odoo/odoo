import { assertType, onWillStart, Plugin, t, usePlugin, whenReady } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { ORM } from "@web/core/orm_plugin";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { PopoverPlugin } from "@web/core/popover/popover_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { redirect } from "@web/core/utils/urls";
import { useEnv } from "@web/owl2/utils";
import { session } from "@web/session";
import { TourRecorderPlugin } from "@web_tour/tour_recorder/tour_recorder_plugin";
import { tourState } from "@web_tour/tour_state";
import { OnboardingItem } from "@web_tour/widgets/onboarding_item";

const stepSchema = {
    trigger: t.string(),
    id: t.string().optional(),
    isActive: t.array(t.string()).optional(),
    run: t
        .customValidator(
            t.or([t.string(), t.function()]),
            (fn) => typeof fn === "string" || !/\{\s*\}$/.test(fn.toString().trim()),
            "run must be a string or a non-empty function"
        )
        .optional(),
};

const stepSchemaAuto = {
    ...stepSchema,
    content: t.string().optional(),
    expectUnloadPage: t.boolean().optional(),
    timeout: t.customValidator(t.number(), (value) => value >= 0 && value <= 60000).optional(),
    tooltipPosition: t
        .customValidator(t.string(), (value) => ["top", "bottom", "left", "right"].includes(value))
        .optional(),
};

const stepSchemaOnboarding = {
    ...stepSchema,
    content: t.or([t.string(), t.object()]).optional(), //allow object(_t && markup)
    tooltipPosition: t
        .customValidator(t.string(), (value) => ["top", "bottom", "left", "right"].includes(value))
        .optional(),
};

const stepSchemaDebug = {
    ...stepSchemaAuto,
    ...stepSchemaOnboarding,
    pause: t.boolean().optional(),
    break: t.boolean().optional(),
};

const tourSchema = {
    steps: t.function(),
};

const tourRegistry = registry.category("web_tour.tours");
tourRegistry.addValidation(t.strictObject(tourSchema));

export class TourPlugin extends Plugin {
    env = useEnv();
    orm = usePlugin(ORM);
    effect = usePlugin(EffectPlugin);
    overlay = usePlugin(OverlayPlugin);
    popover = usePlugin(PopoverPlugin);
    ui = usePlugin(UIPlugin);
    recorder = usePlugin(TourRecorderPlugin);

    toursEnabled = session?.tour_enabled;

    setup() {
        onWillStart(() => this.bootstrap());
    }

    async bootstrap() {
        await whenReady();
        this.addOnboardingItemInDebugMenu();

        if (window.frameElement) {
            return;
        }

        const paramsTourName = new URLSearchParams(browser.location.search).get("tour");
        if (paramsTourName) {
            this.startTour(paramsTourName, { mode: "manual" });
        }

        if (tourState.getCurrentTour()) {
            const currentConfig = tourState.getCurrentConfig();
            if (currentConfig.mode === "auto" || currentConfig.robot || this.toursEnabled) {
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
     * @param {string} name The name of the tour
     */
    async getTour(name, options) {
        // Onboarding tour (come from database (.xml files))
        if (options.mode === "manual") {
            const tour = await this.orm.call("web_tour.tour", "get_tour_json_by_name", [name]);
            if (!tour) {
                console.error(`Tour '${name}' is not found in the database.`);
                return;
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
                console.error(`Tour '${name}' is not found in registry 'web_tour.tours'.`);
                return;
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
            if (!odoo.loader.modules.get("@web_tour/tour_automatic/tour_automatic")) {
                await loadBundle("web_tour.automatic", { css: false });
            }
            const { TourAutomatic } = odoo.loader.modules.get(
                "@web_tour/tour_automatic/tour_automatic"
            );
            new TourAutomatic(tour).start();
        } else {
            await loadBundle("web_tour.interactive");
            const { TourInteractive } = odoo.loader.modules.get(
                "@web_tour/tour_interactive/tour_interactive"
            );
            new TourInteractive(tour, {
                orm: this.orm,
                effect: this.effect,
                overlay: this.overlay,
                popover: this.popover,
                ui: this.ui,
                onChainNextTour: (nextTour) =>
                    this.startTour(nextTour.name, {
                        mode: "manual",
                        redirect: false,
                        rainbowManMessage: nextTour.rainbowManMessage,
                    }),
            }).start(this.env);
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
        this.recorder.removeTourRecorder();

        if (
            !session.is_public &&
            !this.toursEnabled &&
            options.mode === "manual" &&
            !options.robot
        ) {
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

    /**
     * Validate a step according to {@link stepSchema}.
     * @param {Object} step - The step object to validate.
     */
    validateStep(step) {
        const tourConfig = tourState.getCurrentConfig();
        const isActiveArray = Array.isArray(step.isActive) ? step.isActive : [];
        const mode = isActiveArray.includes("auto")
            ? "auto"
            : isActiveArray.includes("manual")
            ? "manual"
            : tourConfig.mode;
        const schema = tourConfig.debug
            ? t.strictObject(stepSchemaDebug)
            : mode === "auto"
            ? t.strictObject(stepSchemaAuto)
            : t.strictObject(stepSchemaOnboarding);
        try {
            assertType(step, schema, "Error in schema for TourStep");
        } catch (error) {
            console.error(error.message);
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
    dependencies: ["orm", "effect", "overlay", "localization"],
    start() {
        const service = usePlugin(TourPlugin);
        odoo.startTour = service.startTour.bind(service);
        odoo.isTourReady = service.isTourReady.bind(service);
        return service;
    },
};
registry.category("services").add("tour_service", tourService);
