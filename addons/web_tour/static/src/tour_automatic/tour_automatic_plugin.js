import { assertType, Plugin, t, usePlugin } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { stepSchemaAuto, stepSchemaDebugAuto } from "@web_tour/tour_schemas";

const tourRegistry = registry.category("web_tour.tours");

export class TourAutomaticPlugin extends Plugin {
    /**
     * Validate a step according to {@link stepSchemaAuto}.
     * @param {Object} step - The step object to validate.
     * @param {boolean} [debug=false]
     */
    validateStep(step, debug = false) {
        const schema = debug ? t.strictObject(stepSchemaDebugAuto) : t.strictObject(stepSchemaAuto);
        try {
            assertType(step, schema, "Error in schema for TourStep");
        } catch (error) {
            console.error(error.message);
        }
    }

    /**
     * Automatic tours come from the client-side `web_tour.tours` registry.
     * @param {string} name The name of the tour
     */
    async getTour(name) {
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
     * Plays an automatic tour (test tours, registered in the client-side
     * `web_tour.tours` registry).
     * @param {Object} tour
     */
    async play(tour) {
        if (!odoo.loader.modules.get("@web_tour/tour_automatic/tour_automatic")) {
            await loadBundle("web_tour.automatic", { css: false });
        }
        const { TourAutomatic } = odoo.loader.modules.get(
            "@web_tour/tour_automatic/tour_automatic"
        );
        await new TourAutomatic(tour).start();
    }
}

services.add(TourAutomaticPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the tour_automatic_service service are removed
 * -----------------------------------------------------------------------------
 */
export const tourAutomaticService = {
    start() {
        return usePlugin(TourAutomaticPlugin);
    },
};

registry.category("services").add("tour_automatic_service", tourAutomaticService);
