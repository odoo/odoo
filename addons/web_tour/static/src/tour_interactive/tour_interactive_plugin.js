import { assertType, Component, markup, Plugin, t, usePlugin } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { loadBundle } from "@web/core/assets";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { ORM } from "@web/core/orm_plugin";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { session } from "@web/session";
import { useEnv } from "@web/owl2/utils";
import { pointerState } from "@web_tour/tour_pointer/tour_pointer";
import { tourState } from "@web_tour/tour_state";
import { stepSchemaOnboarding, stepSchemaDebugOnboarding } from "@web_tour/tour_schemas";

class OnboardingItem extends Component {
    static components = { DropdownItem };
    static template = "web_tour.OnboardingItem";
    static props = {
        toursEnabled: { type: Boolean },
        toggleItem: { type: Function },
    };
    setup() {}
}

const tourRegistry = registry.category("web_tour.tours");

export class TourInteractivePlugin extends Plugin {
    env = useEnv();
    orm = usePlugin(ORM);
    effect = usePlugin(EffectPlugin);
    overlay = usePlugin(OverlayPlugin);
    removePointer = () => {};

    setup() {
        this.toursEnabled = session?.tour_enabled;
        this.addOnboardingItemInDebugMenu();
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
     * Validate a step according to {@link stepSchemaOnboarding}.
     * @param {Object} step - The step object to validate.
     * @param {boolean} [debug=false]
     */
    validateStep(step, debug = false) {
        const schema = debug
            ? t.strictObject(stepSchemaDebugOnboarding)
            : t.strictObject(stepSchemaOnboarding);
        try {
            assertType(step, schema, "Error in schema for TourStep");
        } catch (error) {
            console.error(error.message);
        }
    }

    /**
     * Onboarding tours come from the database (`web_tour.tour` records).
     * @param {string} name The name of the tour
     */
    async getTour(name) {
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

    /**
     * Plays an interactive (manual/onboarding) tour: shows the tour pointer
     * and starts listening for the step triggers. Resolves once the pointer
     * is ready, not once the tour itself is done (the tour can wait
     * indefinitely for user interaction, and can span a full page reload).
     * @param {Object} tour
     * @param {Object} tourConfig
     * @param {Function} [onTourEnd] called once the tour has fully ended
     *  (after the rainbow man, if any), e.g. to chain the next onboarding tour.
     */
    async play(tour, tourConfig, onTourEnd) {
        await loadBundle("web_tour.interactive");
        const { TourPointer } = odoo.loader.modules.get("@web_tour/tour_pointer/tour_pointer");
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
            "@web_tour/tour_interactive/tour_interactive"
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
            await onTourEnd?.();
        });
    }
}

services.add(TourInteractivePlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the tour_interactive_service service are removed
 * -----------------------------------------------------------------------------
 */
export const tourInteractiveService = {
    dependencies: ["effect", "overlay"],
    start() {
        return usePlugin(TourInteractivePlugin);
    },
};

registry.category("services").add("tour_interactive_service", tourInteractiveService);
